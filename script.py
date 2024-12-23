import asyncio
import csv
from howlongtobeatpy import HowLongToBeat

# O usuário deve inserir sua lista de jogos aqui
games_data = {
    "Games": [
        # Exemplo de jogos, o usuário pode adicionar ou editar conforme necessário
        {
            "Game Title": "Daze Before Christmas",
            "Platform": "SNES",
            "Year": 1994,
            "Genre": "Platform"
        },
        {
            "Game Title": "Alisia Dragoon",
            "Platform": "Mega Drive",
            "Year": 1992,
            "Genre": "Action"
        },
        {
            "Game Title": "Growl",
            "Platform": "Mega Drive",
            "Year": 1991,
            "Genre": "Beat 'em up"
        },
        {
            "Game Title": "Thrill Kill",
            "Platform": "PS1",
            "Year": 1998,
            "Genre": "Fighting"
        },
        {
            "Game Title": "Hogs of War",
            "Platform": "PS1",
            "Year": 2000,
            "Genre": "Strategy"
        },
        {
            "Game Title": "Brave Fencer Musashi",
            "Platform": "PS1",
            "Year": 1998,
            "Genre": "Action RPG"
        },
        {
            "Game Title": "Deception III: Dark Delusion",
            "Platform": "PS1",
            "Year": 1999,
            "Genre": "Strategy"
        },
        {
            "Game Title": "The Misadventures of Tron Bonne",
            "Platform": "PS1",
            "Year": 1999,
            "Genre": "Action"
        }
    ]
}

async def add_game_ids(games_data):
    total_games = len(games_data["Games"])
    for index, game in enumerate(games_data["Games"], start=1):
        game_title = game["Game Title"]
        # Realiza a busca assíncrona
        results_list = await HowLongToBeat().async_search(game_title)
        if results_list is not None and len(results_list) > 0:
            # Pega o elemento com maior similaridade
            best_element = max(results_list, key=lambda element: element.similarity)
            # Adiciona o game_id e main_story ao objeto do jogo
            game["Game ID"] = best_element.game_id
            game["Main Story"] = best_element.main_story
        # Imprime o progresso
        print(f"Processed {index}/{total_games} games")

# Executa a função assíncrona
asyncio.run(add_game_ids(games_data))

# Transforma a lista de objetos em um CSV
csv_file = "games_data.csv"
csv_columns = ["Game Title", "Platform", "Year", "Genre", "Game ID", "Main Story"]

try:
    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=csv_columns)
        writer.writeheader()
        for game in games_data["Games"]:
            writer.writerow(game)
    print(f"CSV file '{csv_file}' created successfully.")
except IOError:
    print("I/O error")

# Verifica o resultado
print(games_data)
