import asyncio
import csv
import os
from dotenv import load_dotenv
from howlongtobeatpy import HowLongToBeat
from openai import AsyncOpenAI

# Load environment variables
load_dotenv()

# Initialize API clients
hltb = HowLongToBeat()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Limit the number of concurrent games being processed
# 5 is a safe number to avoid rate limits and keep logs readable
MAX_CONCURRENT_GAMES = 5
semaphore = asyncio.Semaphore(MAX_CONCURRENT_GAMES)

async def get_genre(game_name, platform):
    """Fetches the game genre using OpenAI API."""
    try:
        completion = await client.chat.completions.create(
            model="o4-mini",
            messages=[
                {"role": "system", "content": '''
You are a video game database expert. Your sole purpose is to classify video games into specific genres.

When the user provides a "Game Title - Platform", you must output ONLY the genre name from the following allowed list:
- Action
- Action Adventure
- Action Platformer
- Action RPG
- Adventure
- Beat 'em up
- Fighting
- Metroidvania
- Mini-game
- Pinball
- Platformer
- Puzzle
- Puzzle Platformer
- Racing
- RPG
- Run and Gun
- Shoot 'em up
- Shooter
- Sports
- Strategy
- Survival Horror
- Visual Novel

Constraints:
1. NO conversational filler (e.g., do not say "The genre is..." or "Sure!").
2. NO punctuation at the end of the response.
3. If a game fits multiple categories, choose the most defining one.
4. Output must be in English.
                '''},
                {"role": "user", "content": f"{game_name} - {platform}"}
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"\nError fetching genre for {game_name}: {e}")
        return "Unknown"

async def process_single_game(game, index, total_games):
    """Processes a single game instance with concurrency control."""
    async with semaphore:
        # Initialize default values if empty
        for field in ["Year", "Genre", "Time to Beat", "Score", "Platform"]:
            if not game.get(field) or game[field].strip() == "":
                game[field] = "Unknown"

        game_name = game["Game"]
        platform = game["Platform"]
        
        # Parallelize HLTB and OpenAI calls for this specific game
        hltb_task = hltb.async_search(game_name)
        genre_task = get_genre(game_name, platform) if game["Genre"] == "Unknown" else asyncio.sleep(0, game["Genre"])
        
        try:
            results_list, genre = await asyncio.gather(hltb_task, genre_task)
            game["Genre"] = genre if genre else "Unknown"

            if results_list and len(results_list) > 0:
                best_element = max(results_list, key=lambda element: element.similarity)
                if best_element.similarity > 0.90:
                    game["Score"] = str(best_element.review_score) if best_element.review_score else "Unknown"
                    game["Year"] = str(best_element.release_world) if best_element.release_world else "Unknown"
                    game["Time to Beat"] = str(best_element.main_story) if best_element.main_story else "Unknown"
                    print(f"[{index}/{total_games}] {game_name}: Found! (Sim: {best_element.similarity:.2f} | Genre: {game['Genre']})")
                else:
                    print(f"[{index}/{total_games}] {game_name}: Skipped HLTB (Low Sim: {best_element.similarity:.2f} | Genre: {game['Genre']})")
            else:
                print(f"[{index}/{total_games}] {game_name}: HLTB Not found (Genre: {game['Genre']})")
        except Exception as e:
            print(f"[{index}/{total_games}] Error processing {game_name}: {e}")

async def process_games(input_file, output_file):
    # 1. Read the CSV file
    try:
        with open(input_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            games = list(reader)
    except FileNotFoundError:
        print(f"Error: The file '{input_file}' was not found.")
        return

    total_games = len(games)
    print(f"Starting parallel processing of {total_games} games (Concurrency: {MAX_CONCURRENT_GAMES})...")

    # 2. Create tasks for all games
    tasks = [process_single_game(game, i, total_games) for i, game in enumerate(games, start=1)]
    
    # 3. Run all tasks concurrently
    await asyncio.gather(*tasks)

    # 4. Save results
    fieldnames = ["Game", "Platform", "Year", "Genre", "Time to Beat", "Score", "Status"]
    try:
        with open(output_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(games)
        print(f"\nSuccess! File '{output_file}' created with updated data.")
    except IOError:
        print("\nError: Could not save the CSV file.")

if __name__ == "__main__":
    INPUT_CSV = "games.csv"
    OUTPUT_CSV = "games_updated.csv"
    asyncio.run(process_games(INPUT_CSV, OUTPUT_CSV))
