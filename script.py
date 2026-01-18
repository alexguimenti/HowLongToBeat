import asyncio
import csv
from howlongtobeatpy import HowLongToBeat

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
    hltb = HowLongToBeat()

    print(f"Starting processing of {total_games} games...")

    # 2. Process each game
    for index, game in enumerate(games, start=1):
        game_name = game["Game"]
        print(f"[{index}/{total_games}] Searching: {game_name}...", end=" ", flush=True)
        
        try:
            results_list = await hltb.async_search(game_name)
            
            if results_list and len(results_list) > 0:
                # Get the element with highest similarity
                best_element = max(results_list, key=lambda element: element.similarity)
                
                # Check if similarity is above 0.90
                if best_element.similarity > 0.90:
                    game["Score"] = best_element.review_score
                    game["Year"] = best_element.release_world
                    game["Time to Beat"] = best_element.main_story
                    print(f"Found! (Similarity: {best_element.similarity:.2f})")
                else:
                    print(f"Skipped (Low similarity: {best_element.similarity:.2f})")
            else:
                print("Not found")
                
        except Exception as e:
            print(f"Error searching: {e}")

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
