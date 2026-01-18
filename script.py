import asyncio
import csv
import os
import json
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
    CACHE_FILE = "game_data_cache.json"
    MAX_GAMES_TO_PROCESS = 20
    MAX_CONCURRENT_GAMES = 5
    GENRE_BATCH_SIZE = 20  # Number of games to send to LLM in one request
    SIMILARITY_THRESHOLD = 0.85
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
    """Normalizes empty, null, 'nan' or 'unknown' fields to 'Unknown'."""
    clean_val = str(val or "").strip()
    if clean_val.lower() in ["", "none", "nan", "null", "unknown"]:
        return "Unknown"
    return clean_val

# --- CORE ENGINE ---

class GameEnricher:
    """Manages API clients and the game enrichment process."""
    def __init__(self):
        self.hltb = HowLongToBeat()
        self.openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_GAMES)
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.game_cache: Dict[str, Dict[str, str]] = self._load_cache()

    def _load_cache(self) -> Dict[str, Dict[str, str]]:
        """Loads the game data cache from a local JSON file."""
        if os.path.exists(Config.CACHE_FILE):
            try:
                with open(Config.CACHE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Cache Load Warning: {e}")
        return {}

    def _save_cache(self):
        """Saves the current game data cache to a local JSON file."""
        try:
            with open(Config.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.game_cache, f, indent=2)
        except Exception as e:
            print(f"Cache Save Error: {e}")

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
        # Only process games where Genre is actually empty (not 'Unknown')
        target_games = [g for g in games_to_process if not g.get("Genre") or g["Genre"].strip() == ""]
        
        if not target_games:
            return

        # 1. Check cache first
        remaining_games = []
        for g in target_games:
            cache_key = g["Game"].lower().strip()
            if cache_key in self.game_cache and self.game_cache[cache_key].get("Genre"):
                g["Genre"] = self.game_cache[cache_key]["Genre"]
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
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": f"""
You are a video game database expert. Classify the provided games into ONE genre from: {', '.join(Config.GENRES_ALLOWED)}.
Respond ONLY with a JSON object where the keys are the EXACT game names provided and the values are their genres.
Example: {{"Game Name": "Action", "Another Game": "RPG"}}
                        """},
                        {"role": "user", "content": f"Classify these games: {', '.join([g['Game'] for g in batch])}"}
                    ]
                )
                
                # Parse JSON response
                result_json = json.loads(completion.choices[0].message.content)
                
                # Track usage
                if completion.usage:
                    self.total_prompt_tokens += completion.usage.prompt_tokens
                    self.total_completion_tokens += completion.usage.completion_tokens

                # Update cache and local games
                for game_name, genre in result_json.items():
                    if genre in Config.GENRES_ALLOWED:
                        key = game_name.lower().strip()
                        if key not in self.game_cache:
                            self.game_cache[key] = {}
                        self.game_cache[key]["Genre"] = genre

                # Apply results from cache back to games
                for g in batch:
                    key = g["Game"].lower().strip()
                    if key in self.game_cache and self.game_cache[key].get("Genre"):
                        g["Genre"] = self.game_cache[key]["Genre"]

                # Save cache after each successful batch
                self._save_cache()

            except Exception as e:
                print(f"Batch Processing Error: {e}")

    async def process_hltb_only(self, game: Dict, index: int, total: int):
        """Processes HLTB data for a single game instance."""
        async with self.semaphore:
            name = game["Game"]
            platform = game.get("Platform", "").strip().lower()
            
            # Skip Pico 8 games as they are not on HLTB
            if "pico 8" in platform:
                return

            # Check if we really need HLTB (only if fields are EMPTY, not "Unknown")
            needs_hltb = any(
                not game.get(f) or str(game.get(f)).strip() == "" 
                for f in ["Year", "Game Id", "Time to Beat", "Score"]
            )

            if not needs_hltb:
                return

            # Check cache for HLTB data first
            key = name.lower().strip()
            if key in self.game_cache:
                cached_data = self.game_cache[key]
                # If we have at least Game Id and Year, we consider it cached
                if cached_data.get("Game Id") and cached_data.get("Year"):
                    game["Score"] = cached_data.get("Score", "Unknown")
                    game["Year"] = cached_data.get("Year", "Unknown")
                    game["Game Id"] = cached_data.get("Game Id", "Unknown")
                    game["Time to Beat"] = cached_data.get("Time to Beat", "Unknown")
                    print(f"[{index}/{total}] {name}: Data restored from Cache")
                    return

            try:
                results = await self.hltb.async_search(name)
                if results:
                    best = max(results, key=lambda x: x.similarity)
                    if best.similarity >= Config.SIMILARITY_THRESHOLD:
                        # Prepare data
                        score = normalize_field(best.review_score)
                        year = normalize_field(best.release_world)
                        gid = normalize_field(best.game_id)
                        ttb = round_to_quarter(best.main_story)
                        
                        # Apply to current game
                        game["Score"] = score
                        game["Year"] = year
                        game["Game Id"] = gid
                        game["Time to Beat"] = ttb
                        
                        # Store in cache
                        if key not in self.game_cache:
                            self.game_cache[key] = {}
                        self.game_cache[key].update({
                            "Score": score,
                            "Year": year,
                            "Game Id": gid,
                            "Time to Beat": ttb
                        })
                        self._save_cache()
                        
                        print(f"[{index}/{total}] {name}: HLTB Data Updated (Sim: {best.similarity:.2f})")
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

    # 2. Identify games needing updates (ONLY if fields are TRULY empty)
    to_process = [
        game for game in all_games if any(
            not game.get(f) or str(game.get(f)).strip() == "" 
            for f in ["Year", "Genre", "Game Id", "Time to Beat", "Score"]
        )
    ]

    # 3. Apply processing limit
    queue = to_process[:Config.MAX_GAMES_TO_PROCESS] if Config.MAX_GAMES_TO_PROCESS else to_process
    
    if not queue:
        print("Verification: All games are up to date.")
        return

    print(f"Status: Processing {len(queue)} games...")

    # 4. STEP ONE: Fetch Genres in Batch (Saves a lot of tokens)
    await enricher.fetch_genres_batch(queue)

    # 5. STEP TWO: Fetch HLTB data concurrently
    tasks = [
        enricher.process_hltb_only(game, i, len(queue)) 
        for i, game in enumerate(queue, start=1)
    ]
    await asyncio.gather(*tasks)

    # 6. Post-process the queue: Normalize remaining empties and round times
    for game in queue:
        for field in ["Year", "Genre", "Game Id", "Time to Beat", "Score", "Platform"]:
            game[field] = normalize_field(game.get(field))
        game["Time to Beat"] = round_to_quarter(game["Time to Beat"])

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
