import asyncio
import csv
import os
from typing import List, Dict, Set, Tuple, Optional, Any
from dotenv import load_dotenv
from howlongtobeatpy import HowLongToBeat
from openai import AsyncOpenAI

# --- CONFIGURATION ---
load_dotenv()

class Config:
    """Class to hold script configurations."""
    OVERWRITE_INPUT = True
    INPUT_CSV = "games.csv"
    OUTPUT_CSV = INPUT_CSV if OVERWRITE_INPUT else "games_updated.csv"
    MAX_GAMES_TO_PROCESS = 50
    MAX_CONCURRENT_GAMES = 5
    GENRE_BATCH_SIZE = 20  # Number of games to send to LLM in one request
    SIMILARITY_THRESHOLD = 0.90
    # gpt-4o-mini pricing per 1M tokens (as of early 2024)
    PRICE_PROMPT_1M = 0.15
    PRICE_COMPLETION_1M = 0.60
    GENRES_ALLOWED = [
        "Action", "Action Adventure", "Action Platformer", "Action RPG", "Adventure",
        "Beat 'em up", "Fighting", "Metroidvania", "Mini-game", "Pinball", "Platformer",
        "Puzzle", "Puzzle Platformer", "Racing", "RPG", "Run and Gun", "Shoot 'em up",
        "Shooter", "Sports", "Strategy", "Survival Horror", "Visual Novel"
    ]

# --- UTILITIES ---

def round_to_quarter(value: Optional[str]) -> str:
    """Rounds a time value to the nearest 0.25 increment."""
    if not value or value in ["Unknown", "None", ""]:
        return "Unknown"
    try:
        time_val = float(value)
        rounded = round(time_val * 4) / 4
        return f"{rounded:.2f}"
    except ValueError:
        return "Unknown"

def normalize_field(val: Any) -> str:
    """Normalizes empty, null or 'nan' fields to 'Unknown'."""
    clean_val = str(val or "").strip()
    if clean_val.lower() in ["", "none", "nan", "null"]:
        return "Unknown"
    return clean_val

# --- CORE ENGINE ---

class GameEnricher:
    """Manages API clients and the game enrichment process."""
    def __init__(self):
        self.hltb = HowLongToBeat()
        self.openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_GAMES)
        self.genre_cache: Dict[str, str] = {}
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    def get_cost_summary(self) -> str:
        """Returns a formatted string with token usage and estimated cost."""
        cost = (self.total_prompt_tokens * Config.PRICE_PROMPT_1M / 1_000_000) + \
               (self.total_completion_tokens * Config.PRICE_COMPLETION_1M / 1_000_000)
        return (
            f"\n--- OpenAI Cost Summary ---\n"
            f"Prompt Tokens: {self.total_prompt_tokens}\n"
            f"Completion Tokens: {self.total_completion_tokens}\n"
            f"Total Tokens: {self.total_prompt_tokens + self.total_completion_tokens}\n"
            f"Estimated Cost: ${cost:.6f}"
        )

    async def fetch_genres_batch(self, games_to_process: List[Dict]):
        """Fetches genres for a list of games in batches to save tokens."""
        # 1. Check cache first
        remaining_games = []
        for g in games_to_process:
            cache_key = g["Game"].lower().strip()
            if cache_key in self.genre_cache:
                g["Genre"] = self.genre_cache[cache_key]
            else:
                remaining_games.append(g)

        if not remaining_games:
            return

        # 2. Process in batches
        for i in range(0, len(remaining_games), Config.GENRE_BATCH_SIZE):
            batch = remaining_games[i : i + Config.GENRE_BATCH_SIZE]
            batch_str = "\n".join([f"- {g['Game']} ({g['Platform']})" for g in batch])
            
            try:
                print(f"Token optimization: Fetching genres for a batch of {len(batch)} games...")
                completion = await self.openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": f"""
You are a video game database expert. Classify each game in the list into ONE genre from: {', '.join(Config.GENRES_ALLOWED)}.
Return exactly one line per game in the format 'Game Name: Genre'. 
If you don't know, use 'Unknown'. No filler text.
                        """},
                        {"role": "user", "content": f"Classify these games:\n{batch_str}"}
                    ]
                )
                
                responses = completion.choices[0].message.content.strip().split("\n")
                
                # Track usage
                if completion.usage:
                    self.total_prompt_tokens += completion.usage.prompt_tokens
                    self.total_completion_tokens += completion.usage.completion_tokens
                for line in responses:
                    if ":" in line:
                        parts = line.split(":", 1)
                        # Remove marker "-" if present
                        game_ref = parts[0].strip().lstrip("- ").lower()
                        genre_result = parts[1].strip()
                        if genre_result in Config.GENRES_ALLOWED:
                            self.genre_cache[game_ref] = genre_result

                # Apply results to batch
                for g in batch:
                    key = g["Game"].lower().strip()
                    g["Genre"] = self.genre_cache.get(key, "Unknown")

            except Exception as e:
                print(f"Batch Processing Error: {e}")

    async def process_hltb_only(self, game: Dict, index: int, total: int):
        """Processes HLTB data for a single game instance."""
        async with self.semaphore:
            name = game["Game"]
            
            # Check if we really need HLTB (other fields besides Genre)
            needs_hltb = any(game[f] == "Unknown" for f in ["Year", "Game Id", "Time to Beat", "Score"])

            if not needs_hltb:
                return

            try:
                results = await self.hltb.async_search(name)
                if results:
                    best = max(results, key=lambda x: x.similarity)
                    if best.similarity >= Config.SIMILARITY_THRESHOLD:
                        game["Score"] = normalize_field(best.review_score)
                        game["Year"] = normalize_field(best.release_world)
                        game["Game Id"] = normalize_field(best.game_id)
                        game["Time to Beat"] = round_to_quarter(best.main_story)
                        print(f"[{index}/{total}] {name}: HLTB Data Updated (Sim: {best.similarity:.2f})")
                    else:
                        print(f"[{index}/{total}] {name}: Low HLTB Similarity ({best.similarity:.2f})")
                else:
                    print(f"[{index}/{total}] {name}: Not found on HLTB")
            except Exception as e:
                print(f"[{index}/{total}] {name}: HLTB Error: {e}")

# --- DATA HANDLING ---

def deduplicate_games(games: List[Dict]) -> List[Dict]:
    """Identifies and removes duplicate entries based on Game and Platform."""
    seen: Set[Tuple[str, str]] = set()
    unique_list = []
    
    for game in games:
        name = normalize_field(game.get("Game")).lower()
        plat = normalize_field(game.get("Platform")).lower()
        key = (name, plat)
        
        if key not in seen:
            seen.add(key)
            unique_list.append(game)
    
    duplicates_removed = len(games) - len(unique_list)
    if duplicates_removed > 0:
        print(f"Cleanup: Removed {duplicates_removed} duplicate entries.")
    
    return unique_list

async def main():
    """Main execution flow optimized for cost and performance."""
    enricher = GameEnricher()
    
    # 1. Load and Clean Data
    all_games = []
    try:
        with open(Config.INPUT_CSV, mode='r', encoding='utf-8') as f:
            all_games = deduplicate_games(list(csv.DictReader(f)))
    except FileNotFoundError:
        print(f"Critical Error: File '{Config.INPUT_CSV}' not found.")
        return

    # 2. Normalize and Round existing data
    for game in all_games:
        for field in ["Year", "Genre", "Game Id", "Time to Beat", "Score", "Platform"]:
            game[field] = normalize_field(game.get(field))
        game["Time to Beat"] = round_to_quarter(game["Time to Beat"])

    # 3. Filter games needing any update
    to_process = [
        g for g in all_games if any(
            g[f] == "Unknown" for f in ["Year", "Genre", "Game Id", "Time to Beat", "Score"]
        )
    ]

    # 4. Limit the work queue
    queue = to_process[:Config.MAX_GAMES_TO_PROCESS] if Config.MAX_GAMES_TO_PROCESS else to_process
    
    if not queue:
        print("Verification: All games are up to date.")
        return

    print(f"Status: Processing {len(queue)} games...")

    # 5. STEP ONE: Fetch Genres in Batch (Saves a lot of tokens)
    needing_genre = [g for g in queue if g["Genre"] == "Unknown"]
    if needing_genre:
        await enricher.fetch_genres_batch(needing_genre)

    # 6. STEP TWO: Fetch HLTB data concurrently
    tasks = [
        enricher.process_hltb_only(game, i, len(queue)) 
        for i, game in enumerate(queue, start=1)
    ]
    await asyncio.gather(*tasks)

    # 7. Print OpenAI Usage Summary
    print(enricher.get_cost_summary())

    # 8. Save results
    fieldnames = ["Game", "Platform", "Year", "Genre", "Game Id", "Time to Beat", "Score", "Status"]
    try:
        with open(Config.OUTPUT_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_games)
        print(f"\nSuccess: '{Config.OUTPUT_CSV}' updated. {len(queue)} games processed.")
    except IOError as e:
        print(f"\nError: Failed to save file. {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
