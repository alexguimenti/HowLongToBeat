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
        return ""

async def process_games(input_file, output_file):
    games = []
    
    # 1. Read the CSV file
    try:
        with open(input_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            games = list(reader)
    except FileNotFoundError:
        print(f"Error: The file '{input_file}' was not found.")
        return

    total_games = len(games)
    print(f"Starting processing of {total_games} games...")

    # 2. Process each game
    for index, game in enumerate(games, start=1):
        game_name = game["Game"]
        platform = game.get("Platform", "Unknown")
        print(f"[{index}/{total_games}] Processing: {game_name}...", end=" ", flush=True)
        
        # Parallelize HLTB and OpenAI calls for efficiency
        hltb_task = hltb.async_search(game_name)
        genre_task = get_genre(game_name, platform) if not game.get("Genre") else asyncio.sleep(0, game["Genre"])
        
        try:
            results_list, genre = await asyncio.gather(hltb_task, genre_task)
            
            # Update Genre
            if genre:
                game["Genre"] = genre

            # Update HLTB data
            if results_list and len(results_list) > 0:
                best_element = max(results_list, key=lambda element: element.similarity)
                
                if best_element.similarity > 0.90:
                    game["Score"] = best_element.review_score
                    game["Year"] = best_element.release_world
                    game["Time to Beat"] = best_element.main_story
                    print(f"Found! (Similarity: {best_element.similarity:.2f} | Genre: {genre})")
                else:
                    print(f"Skipped HLTB (Low similarity: {best_element.similarity:.2f} | Genre: {genre})")
            else:
                print(f"HLTB Not found (Genre: {genre})")
                
        except Exception as e:
            print(f"Error processing {game_name}: {e}")

    # 3. Save results to the new CSV
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
