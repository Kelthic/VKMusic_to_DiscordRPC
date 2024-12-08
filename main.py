import configparser
import time
import requests
import pypresence
from chardet.universaldetector import UniversalDetector

print("Программа инициализируется...")

# Чтение конфигурации
config = configparser.ConfigParser()
detector = UniversalDetector()
with open('config.ini', 'rb') as fh:
    for line in fh:
        detector.feed(line)
        if detector.done:
            break
    detector.close()
config.read("config.ini", encoding=detector.result["encoding"])

# Получаем app_id из конфигурации
app_id = config['Discord']['app_id']


def get_user_status(user_token, user_id):
    """Получаем статус пользователя и текущую музыку."""
    url = f"https://api.vk.com/method/users.get?user_ids={user_id}&fields=status,status_audio&access_token={user_token}&v=5.131"
    return requests.get(url).json()


def get_track_info(owner_id, audio_id, user_token):
    """Получаем информацию о треке и его обложку."""
    url = f"https://api.vk.com/method/audio.getById?audios={owner_id}_{audio_id}&access_token={user_token}&v=5.131"
    return requests.get(url).json()


def format_time(seconds):
    """Форматирует время в формате MM:SS."""
    minutes = seconds // 60
    seconds %= 60
    return f"{minutes:02}:{seconds:02}"


def create_progress_bar(current, total, length=8):
    """Создает текстовый прогрессбар."""
    progress = int((current / total) * length)
    return f"[{'▰' * progress}{'▱' * (length - progress)}]"


def run():
    try:
        presence = pypresence.Presence(app_id)
        presence.connect()

        user_token = config['VK']['user_token']
        user_id = config['VK']['id']

        print("Приложение было проинициализировано. Запуск через 5 секунд.")
        time.sleep(5)

        # Переменные для отслеживания прогресса и информации о треке
        last_track_id = None
        last_artist = None
        last_title = None
        last_image_url = None
        track_start_time = None

        while True:
            default_image = "https://sun9-50.userapi.com/impg/ZvkDRL4FWR-mF3kdYTKMzG811xV6kj4jBtiy8A/xbgImcIHYgc.jpg?size=1024x1024&quality=95&sign=c0a95ce9e37c55f35f72dc18ca8471eb&type=album"
            activity = {"large_image": default_image}

            user_status = get_user_status(user_token, user_id)
            if 'response' not in user_status or len(user_status['response']) == 0:
                print("Не удалось получить статус пользователя.")
                continue

            res = user_status['response'][0]

            if "status_audio" not in res:
                state = "🎧 No playable music."
                activity.update({'state': state})
            else:
                curr_music = res['status_audio']
                state = f""
                details = f"🗣Artist: {curr_music['artist']} | 📜Title: {curr_music['title']}"

                # Проверка, изменились ли данные
                artist = curr_music['artist']
                title = curr_music['title']
                release_id = curr_music.get("release_audio_id")
                large_image = default_image

                if release_id:
                    owner_id, audio_id = release_id.split('_')
                    track_info = get_track_info(owner_id, audio_id, user_token)

                    if 'response' in track_info and len(track_info['response']) > 0:
                        track_data = track_info['response'][0]
                        album = track_data.get('album', {})
                        large_image = album.get('thumb', {}).get('photo_270', default_image)

                # Если информация о треке изменилась, выводим в консоль
                if artist != last_artist or title != last_title or large_image != last_image_url:
                    print("\n-----------------------------")
                    print(f"🎶 New track info:")
                    print(f"🗣 Artist: {artist}")
                    print(f"📜 Title: {title}")
                    print(f"🖼 Cover Image URL: {large_image}")
                    print("-----------------------------\n")

                    # Обновляем последние значения
                    last_artist = artist
                    last_title = title
                    last_image_url = large_image

                duration = int(curr_music.get('duration', 1))  # Преобразуем в целое число
                stream_duration = 0  # Инициализация переменной перед использованием

                # Если трек изменился, сбрасываем прогресс
                if curr_music['id'] != last_track_id:
                    last_track_id = curr_music['id']
                    track_start_time = time.time()  # Фиксируем время старта трека
                else:
                    # Увеличиваем `stream_duration` на основании времени
                    stream_duration = int(min(time.time() - track_start_time, duration))  # Преобразуем в целое число

                elapsed_time = format_time(stream_duration)  # Преобразуем stream_duration в целое число
                total_time = format_time(duration)  # Преобразуем duration в целое число
                progress_bar = create_progress_bar(stream_duration, duration)

                state += f"\n{progress_bar} {elapsed_time} / {total_time}"

                activity.update({'state': state, 'details': details, 'large_image': large_image})

            presence.update(**activity)
            time.sleep(5)  # Интервал обновления статуса и прогрессбара

    except OSError:
        print("Ошибка подключения. Перезапуск...")
        run()


if __name__ == "__main__":
    run()
