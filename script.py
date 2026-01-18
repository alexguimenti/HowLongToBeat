import asyncio
import csv
from howlongtobeatpy import HowLongToBeat

async def process_games(input_file, output_file):
    games = []
    
    # 1. Ler o arquivo CSV
    try:
        with open(input_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            games = list(reader)
    except FileNotFoundError:
        print(f"Erro: O arquivo '{input_file}' não foi encontrado.")
        return

    total_games = len(games)
    hltb = HowLongToBeat()

    print(f"Iniciando processamento de {total_games} jogos...")

    # 2. Processar cada jogo
    for index, game in enumerate(games, start=1):
        game_name = game["Game"]
        print(f"[{index}/{total_games}] Procurando: {game_name}...", end=" ", flush=True)
        
        try:
            results_list = await hltb.async_search(game_name)
            
            if results_list and len(results_list) > 0:
                # Pega o elemento com maior similaridade
                best_element = max(results_list, key=lambda element: element.similarity)
                
                # Valida se a similaridade é maior que 0.90
                if best_element.similarity > 0.90:
                    game["Score"] = best_element.review_score
                    game["Year"] = best_element.release_world
                    game["Time to Beat"] = best_element.main_story
                    print(f"Encontrado! (Sim: {best_element.similarity:.2f})")
                else:
                    print(f"Pulado (Similaridade baixa: {best_element.similarity:.2f})")
            else:
                print("Não encontrado")
                
        except Exception as e:
            print(f"Erro ao buscar: {e}")

    # 3. Salvar o resultado no novo CSV
    fieldnames = ["Game", "Platform", "Year", "Genre", "Time to Beat", "Score", "Status"]
    try:
        with open(output_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(games)
        print(f"\nSucesso! Arquivo '{output_file}' criado com os dados atualizados.")
    except IOError:
        print("\nErro: Não foi possível salvar o arquivo CSV.")

if __name__ == "__main__":
    INPUT_CSV = "games.csv"
    OUTPUT_CSV = "games_updated.csv"
    
    asyncio.run(process_games(INPUT_CSV, OUTPUT_CSV))
