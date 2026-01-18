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
    SIMILARITY_THRESHOLD = 0.90
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
        # Converting to float and rounding to nearest 0.25
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

    async def fetch_genre(self, game_name: str, platform: str) -> str:
        """Classifies the game genre using OpenAI API."""
        try:
            completion = await self.openai.chat.completions.create(
                model="o4-mini",
                messages=[
                    {"role": "system", "content": f"""
You are a video game database expert. Your sole purpose is to classify video games into specific genres.
Output ONLY the genre name from the following allowed list: {', '.join(Config.GENRES_ALLOWED)}.
No conversational filler. No punctuation at the end. Output in English.
                    """},
                    {"role": "user", "content": f"{game_name} - {platform}"}
                ]
            )
            genre = completion.choices[0].message.content.strip()
            return genre if genre in Config.GENRES_ALLOWED else "Unknown"
        except Exception as e:
            print(f"\n[OpenAI Error] {game_name}: {e}")
            return "Unknown"

    async def process_single_game(self, game: Dict, index: int, total: int):
        """Orchestrates the update process for a single game instance."""
        async with self.semaphore:
            # 1. Initial Normalization
            for field in ["Year", "Genre", "Game Id", "Time to Beat", "Score", "Platform"]:
                game[field] = normalize_field(game.get(field))
            
            # Normalize existing time format
            game["Time to Beat"] = round_to_quarter(game["Time to Beat"])

            name, plat = game["Game"], game["Platform"]
            
            # Check if we need to call APIs
            needs_hltb = any(game[f] == "Unknown" for f in ["Year", "Game Id", "Time to Beat", "Score"])
            needs_genre = game["Genre"] == "Unknown"

            if not needs_hltb and not needs_genre:
                return # Row is already complete

            # 2. Parallel API Calls
            hltb_task = self.hltb.async_search(name) if needs_hltb else asyncio.sleep(0, None)
            genre_task = self.fetch_genre(name, plat) if needs_genre else asyncio.sleep(0, game["Genre"])
            
            try:
                hltb_results, genre = await asyncio.gather(hltb_task, genre_task)
                
                # Update genre regardless of HLTB result if needed
                if needs_genre:
                    game["Genre"] = genre

                # Update HLTB data if found and similar enough
                if needs_hltb and hltb_results:
                    best = max(hltb_results, key=lambda x: x.similarity)
                    if best.similarity >= Config.SIMILARITY_THRESHOLD:
                        game["Score"] = normalize_field(best.review_score)
                        game["Year"] = normalize_field(best.release_world)
                        game["Game Id"] = normalize_field(best.game_id)
                        game["Time to Beat"] = round_to_quarter(best.main_story)
                        print(f"[{index}/{total}] {name}: Updated (Sim: {best.similarity:.2f})")
                        return
                    
                status_msg = "Genre updated" if needs_genre else "Skipped (Low similarity or not found)"
                print(f"[{index}/{total}] {name}: {status_msg}")

            except Exception as e:
                print(f"[{index}/{total}] Error refining {name}: {e}")

# --- DATA HANDLING ---

def deduplicate_games(games: List[Dict]) -> List[Dict]:
    """Identifies and removes duplicate entries based on Game and Platform."""
    seen: Set[Tuple[str, str]] = set()
    unique_list = []
    
    for game in games:
        # Create a unique normalized key
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
    """Main execution flow."""
    enricher = GameEnricher()
    
    # 1. Load Data
    all_games = []
    try:
        with open(Config.INPUT_CSV, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            all_games = deduplicate_games(list(reader))
    except FileNotFoundError:
        print(f"Critical Error: File '{Config.INPUT_CSV}' not found.")
        return

    # 2. Identify games needing updates
    games_needing_update = [
        game for game in all_games if any(
            normalize_field(game.get(f)) == "Unknown" 
            for f in ["Year", "Genre", "Game Id", "Time to Beat", "Score"]
        )
    ]

    # 3. Apply processing limit
    if Config.MAX_GAMES_TO_PROCESS is not None:
        process_queue = games_needing_update[:Config.MAX_GAMES_TO_PROCESS]
    else:
        process_queue = games_needing_update
    
    total_to_process = len(process_queue)
    if total_to_process == 0:
        print("Verification: All processed games are up to date.")
        return

    print(f"Status: Found {len(all_games)} games. Processing {total_to_process} items...")

    # 4. Execute enrichment tasks concurrently
    tasks = [
        enricher.process_single_game(game, i, total_to_process) 
        for i, game in enumerate(process_queue, start=1)
    ]
    await asyncio.gather(*tasks)

    # 5. Save results
    fieldnames = ["Game", "Platform", "Year", "Genre", "Game Id", "Time to Beat", "Score", "Status"]
    try:
        with open(Config.OUTPUT_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_games)
        print(f"\nSuccess: '{Config.OUTPUT_CSV}' has been updated.")
    except IOError as e:
        print(f"\nError: Failed to save file. {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
