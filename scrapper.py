import psycopg2
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from bs4 import BeautifulSoup
import requests
import json
import urllib.parse
from time import sleep
import os
from dotenv import load_dotenv
load_dotenv()


serivce = ChromeService(
    executable_path="chromedriver/chromedriver_mac64/chromedriver.exe")

BILLBOARDS_YEAR_URL = "https://www.billboard.com/charts/year-end/"
BILLBOARDS_80S_URL = " https://www.billboard.com/charts/greatest-billboards-top-songs-80s/"
SOUNDCLOUD_URL = "https://soundcloud.com/search/sounds?q="
START_YEAR = 2006
END_YEAR = 2022


def create_driver():
    return webdriver.Chrome(service=serivce)


def generate_top_100_songs(year):
    url = BILLBOARDS_YEAR_URL + str(year) + "/hot-100-songs"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')

    entries = soup.find_all(
        "div", {'class': 'o-chart-results-list-row-container'})

    songs = []
    for entry in entries:
        title_tag = entry.find("h3", {'id': 'title-of-a-story'})
        if title_tag is None:
            break
        title, artist = (title_tag.get_text().strip(),
                         title_tag.parent.find('span').get_text().strip())
        songs.append(title + " - " + artist + "\n")

    return songs


def generate_top_100_year_files(start=START_YEAR, end=END_YEAR):
    for year in range(start, end+1):
        with open("songs/" + str(year) + ".txt", "w") as file:
            songs = generate_top_100_songs(year)
            file.writelines(songs)


def generate_top_100_decades_files():
    with open("songs/80s.txt", "w") as file:
        songs = generate_top_100_decades()
        file.writelines(songs)


def generate_top_100_decades():
    """Generates top 100 songs for 80s"""
    r = requests.get(BILLBOARDS_80S_URL)
    soup = BeautifulSoup(r.text, 'html.parser')

    entries = soup.find_all(
        "div", {'class': 'o-chart-results-list-row-container'})

    songs = []
    numSongs = 0
    for entry in entries:
        if numSongs == 100:
            return songs
        title_tag = entry.find("h3", {'id': 'title-of-a-story'})
        if title_tag is None:
            break
        title, artist = (title_tag.get_text().strip(),
                         title_tag.parent.find('span').get_text().strip())
        songs.append(title + " - " + artist + "\n")
        numSongs += 1

    return songs


def parse_file(filename=f"{START_YEAR}.txt"):

    unique_songs = {}

    with open("songs/" + filename, "r") as file:
        songs = file.readlines()
        for song in songs:
            song = song.strip()
            unique_songs[song] = ""

    return unique_songs


def get_soundcloud_link(driver, song):
    try:
        print("Getting soundcloud link for " + song)

        url = SOUNDCLOUD_URL + urllib.parse.quote(song)

        driver.get(url)
        sleep(3)
        html = driver.page_source

        soup = BeautifulSoup(html, 'html.parser')

        song_link = soup.find('div', {'class': 'searchItem'}).find(
            'a', {'sound__coverArt'})['href']
        genre = soup.find('div', {'class': 'searchItem'}).find(
            'a', {'sc-tag'}).get_text().strip()

        return ('https://soundcloud.com' + song_link, genre, None)
    except:
        print("Failed to get soundcloud link for " + song)
        return (None, None, "Failed to get soundcloud link for " + song)


def parse_song_files(driver, filename):
    unique_songs = {}

    if filename:
        unique_songs = parse_file(filename)
    else:
        for filename in os.listdir("songs"):
            with open("songs/" + str(filename), "r") as file:
                songs = file.readlines()
                for song in songs:
                    song = song.strip()
                    unique_songs[song] = ""

    with open("playlist.json", 'w') as file:
        file.write("[\n")

    for song in unique_songs:
        url, genre, err = get_soundcloud_link(driver, song)

        if err:  # if failed to get soundcloud link
            continue

        song_details = {
            "title": song.split(" - ")[0],
            "artist": song.split(" - ")[1],
            "url": url,
            "genre": genre
        }

        if (song_details["url"] != "Failed to get soundcloud link for " + song):
            with open("playlist.json", 'a') as file:
                json.dump(song_details, file, indent=4)
                file.write(',\n')

    with open("playlist.json", 'a') as file:
        file.write(']\n')


def genre_list():
    with open("playlist.json", "r") as file:
        songs = json.load(file)
        genres = []
        for song in songs:
            genres.append(song["genre"])
        genres = list(set(genres))
        print(genres, len(genres))
        return genres


def connect_to_db():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    return conn


def push_to_db():
    conn = connect_to_db()
    db = conn.cursor()
    with open("playlist.json", "r") as file:
        songs = json.load(file)
        for song in songs:
            print(song)
            db.execute('INSERT INTO "Songs"(title, artist, url, genre,name) VALUES (%s, %s, %s, %s, %s)', (song.get(
                "title"), song.get("artist"), song.get("url"), song.get("genre"), song.get("title")+" - "+song.get("artist")))
    conn.commit()

    db.close()
    conn.close()
    print("Done pushing to db")


def main():
    generate_top_100_year_files()
    generate_top_100_decades_files()
    driver = create_driver()
    parse_song_files(driver, None)
    push_to_db()


if __name__ == "__main__":
    main()
