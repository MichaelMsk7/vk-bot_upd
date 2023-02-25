import json
import re
import vk_api
from datetime import datetime
from vk_api.longpoll import VkLongPoll, VkEventType
from random import randrange
from sql_part import db_api


class VKSearchBot:
    relations = {
        1: 'не женат/не замужем',
        2: 'есть друг/есть подруга',
        3: 'помолвлен/помолвлена',
        4: 'женат/замужем',
        5: 'всё сложно',
        6: 'в активном поиске',
        7: 'влюблён/влюблена',
        8: 'в гражданском браке'
    }
    regex = {
        'нижний возрастной порог': 'lower_age_limit',
        'верхний возрастной порог': 'higher_age_limit',
        'город': 'city',
        'семейное положение': 'marital_status'
    }

    def __init__(self, group_token: str):
        """Данный класс представляет собой поисковый бот для нахождения
        людей для отношений."""
        print('Bot was created')
        self.vk = vk_api.VkApi(token=group_token)
        self.user_session = None
        self.longpoll = VkLongPoll(self.vk)
        self.user_info = None
        self.token = None
        self.db_api = db_api

    def start_listening(self):
        """Данный метод предназначен для запуска основного цикла обработки
        сообщений от пользователя с использованием сервера Longpoll."""
        try:
            for event in self.longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW:

                    if event.to_me:
                        message = event.text
                        message_lower = message.lower()
                        self.open_search_session(vk_id=event.user_id)
                        if self.user_session:
                            self.get_info(event.user_id)
                            if message_lower == "привет":
                                if self.user_session:
                                    name = self.user_info['first_name']
                                    text = f'Хай, {name}! Для того, чтобы ' \
                                           f'начать поиск, введите ' \
                                           f'фразу "начать поиск".'
                                    self.write_msg(event.user_id, text)
                            elif message_lower == 'начать поиск':
                                self.get_search_data(event.user_id)
                            elif re.search('город: ', message_lower):
                                self.parse_new_data(event.user_id, message_lower)
                            elif message_lower == "справка":
                                info_text = ''
                                for key, value in self.relations.items():
                                    info_text += str(key) + ' - ' + value + '\n'
                                self.write_msg(event.user_id, info_text)
                            elif message_lower == "пока":
                                self.write_msg(event.user_id, "Пока((")
                            else:
                                self.write_msg(event.user_id, "Не поняла вашего ответа...")
                            self.user_session = None
                            self.user_info = None
                            self.token = None
        except:
            print('Не установлено соединение с сервером!')

    def write_msg(self, user_id: int, message: str):
        """Данный метод предназначен для отправки сообщений пользователю
        от имени сообщества."""
        self.vk.method('messages.send', {'user_id': user_id,
                                         'message': message,
                                         'random_id': randrange(10 ** 7)})

    def send_media(self, user_id: int, media_list: str):
        """Данный метод предназначен для отправки медиаконтента пользователю
        от имени сообщества."""
        params = {
            'user_id': user_id,
            'access_token': self.token,
            'attachment': media_list,
            'random_id': 0
        }
        self.vk.method('messages.send', params)

    @staticmethod
    def user_token_access_url():
        """Данный метод предназначен для формирования ссылки получения
        токена пользователя. Для использования переадресации на
        собственный сервер нужно указать uri для верификации страницы
        сайта на собственном сервере."""
        with open('search_logic/server_configs.json', 'r') as f:
            configs = json.load(f)
        url = f'https://oauth.vk.com/oauth/authorize' \
              f'?client_id={configs["app_id"]}&' \
              f'scope=327694&' \
              f'redirect_uri={configs["server_uri"]}&' \
              f'display=page&' \
              f'response_type=token'
        return url

    def open_search_session(self, vk_id: int):
        """Данный метод проверяет наличие у пользователя токена авторизации
        приложением и отправляет сообщение с url на получение токена, если
        его нет в базе данных tokens."""
        token = self.db_api.check_token(vk_id)
        if token:
            self.user_session = vk_api.VkApi(token=token['token'])
            self.token = token['token']
        else:
            text = f'Вы не авторизованы в нашем приложении! Для ' \
                   f'предоставления доступа пройдите по ' \
                   f'нижеуказанной ссылке:\n{self.user_token_access_url()}'
            self.write_msg(vk_id, text)

    def get_info(self, user_id: int):
        """Получение всей необходимой информации о пользователе из базы
        данных users для сбора статистики и некоторых внутренних
        обработок бота."""
        params = {
            'user_id': user_id,
            'fields': 'sex, contacts, bdate, city, relation'
        }
        try:
            self.user_info = self.user_session.method('users.get', params)[0]
            data_to_write = dict()
            data_to_write['vk_id'] = self.user_info['id']
            data_to_write['age'] = self.count_age(self.user_info['bdate'])
            data_to_write['seen_users'] = None
            data_to_write['city'] = self.user_info['city']['title']
            for key in ['sex', 'first_name', 'last_name']:
                data_to_write[key] = self.user_info[key]
            self.db_api.add_new_user(data_to_write)
        except:
            self.write_msg(user_id, 'Технические неполадки на сервере, '
                                    'обратитесь к данному приложению позже!')

    @staticmethod
    def count_age(time_data: str) -> int:
        """Метод, предназначенный для перевода даты рождения пользователя
        в формате %d.%m.%Y в его возраст в годах путём целочисленного
        деления на 365 (среднее количество дней в году)."""
        date = datetime.strptime(time_data, '%d.%m.%Y')
        current_date = datetime.now()
        delta = current_date - date
        return delta.days//365

    def get_search_data(self, user_id: int):
        """Метод, предназначенный для получения от пользователя данных
        поискового запроса с обращением в таблицу search_params. Если
        для данного пользователя параметры ещё не установлены - появляется
        вспомогательное сообщение о формате заполнения параметров поиска."""
        result = db_api.get_params(user_id)
        if result:
            self.write_msg(user_id, 'Начинаем поиск...')
            try:
                self.search_for_users(user_id)
            except:
                self.write_msg(user_id, "Технические неполадки на сервере, "
                                        "обратитесь к данному приложению "
                                        "позже!")
            return result
        else:
            text = 'Видимо, Вы ещё не вводили параметры поиска своей второй ' \
                   'половинки... Введите параметры следующим образом:\n' \
                   'Нижний возрастной порог: 26, Верхний возрастной порог: ' \
                   '28, Город: Санкт-Петербург, Семейное положение: ' \
                   '1. Справку по значениям семейного положения можно ' \
                   'получить, введя слово "справка".'
            self.write_msg(user_id, text)

    def validate_data(self, data_to_validate: list) -> bool:
        """Данный метод проверяет наличие всех заполненных полей поискового
        запроса."""
        valid_data = True
        for key in self.regex.keys():
            anyone = False
            for data in data_to_validate:
                anyone |= bool(re.search(key, data))
            valid_data &= anyone
        return valid_data

    def parse_new_data(self, user_id: int, text_to_parse: str):
        """Данный метод преобразует текстовое сообщение от пользователя
        с поисковыми параметрами в словарь и записывает его в таблицу
        search_params. В конце отправляется сообщение об успешном
        добавлении и о дальнейших действиях."""
        if db_api.get_params(user_id):
            db_api.delete_params(user_id)
        text_sep_by_comma = text_to_parse.split(', ')
        if re.search('.', text_sep_by_comma[-1]):
            last_word = text_sep_by_comma.pop(-1)
            text_sep_by_comma.append(last_word.split('.')[0])
        if self.validate_data(text_sep_by_comma):
            user_sex = db_api.get_user(user_id)['sex']
            sex_to_search = 1 if user_sex == 2 else 2
            data_to_send = dict()
            data_to_send['sex'] = sex_to_search
            data_to_send['vk_id'] = user_id
            for item in text_sep_by_comma:
                item_separated = item.split(': ')
                key = item_separated[0]
                value = item_separated[1]
                if key in ['нижний возрастной порог',
                           'верхний возрастной порог',
                           'семейное положение']:
                    value = int(value)
                data_to_send[self.regex[key]] = value
            db_api.add_params(data_to_send)
            self.write_msg(user_id, 'Параметры поиска успешно добавлены! '
                                    'Для поиска пары введите команду '
                                    '"начать поиск".')
        else:
            self.write_msg(user_id, 'Данные введены неправильно, '
                                    'попробуйте ещё раз. Введите параметры '
                                    'следующим образом:\nНижний возрастной '
                                    'порог: 26, Верхний возрастной порог: '
                                    '28, Город: Санкт-Петербург, Семейное '
                                    'положение: 1. Справку по значениям '
                                    'семейного положения можно получить, '
                                    'введя слово "справка".')

    def search_for_users(self, user_id: int):
        """Данный метод предназначен для поиска людей по заданным
        пользователем параметрам и отправляет ему сообщение с
        найденными фотографиями и ссылкой на страницу найденного
        пользователя. В конце обновляется поле просмотренных пользователей
        в таблице users."""
        user_data = db_api.get_user(user_id)
        if user_data['found_users']:
            filtered_search_result = user_data['found_users']
        else:
            search_params = db_api.get_params(user_id)
            search_params['age_from'] = search_params.pop('lower_age_limit')
            search_params['age_to'] = search_params.pop('higher_age_limit')
            search_params['city_id'] = self.search_city(
                city_name=search_params.pop('city')
            )
            search_params['status'] = search_params.pop('marital_status')
            params = {
                'has_photo': 1,
                'q': '',
                'count': 1000
            }
            params.update(search_params)
            search_result = self.user_session.method('users.search', params)
            if 'items' in search_result.keys():
                filtered_search_result = list(filter(
                    lambda x: self.check_access(x), search_result['items']))
            else:
                assert Exception('Не были получены данные!')
        if user_data['seen_users']:
            filtered_search_result = list(
                filter(lambda x: x not in user_data['seen_users'],
                       filtered_search_result)
            )
            filtered_ids = [str(elem['id']) for elem in filtered_search_result]
            self.db_api.add_found_users(user_id, filtered_ids)
        gen_rnd_idx = randrange(0, len(filtered_search_result) - 1)
        user_to_suggest = \
            filtered_search_result.pop(gen_rnd_idx)
        filtered_ids = [str(elem['id']) for elem in filtered_search_result]
        user_data['found_users'] = filtered_ids
        self.db_api.add_found_users(user_id, filtered_ids)
        self.find_photos(user_to_suggest)
        if user_data['seen_users']:
            user_data['seen_users'].append(filtered_search_result[gen_rnd_idx]['id'])
        else:
            user_data['seen_users'] = [filtered_search_result[0]['id']]
        user_data['vk_id'] = user_id
        db_api.delete_user(user_id)
        db_api.add_new_user(user_data)

    def search_city(self, city_name: str) -> int:
        """Поиск id города по базе данных сервера ВКонтакте, возвращает
        первый элемент результата поиска."""
        params = {
            'q': city_name,
        }
        result = self.user_session.method('database.getCities', params)
        first_result = result['items'][0]
        return first_result['id']

    @staticmethod
    def check_access(search_data: dict) -> bool:
        """Данная функция-обработка проверяет открыта ли информация
        найденного пользователя для пользователя приложения."""
        if search_data['is_closed']:
            return search_data['can_access_closed']
        return True

    def find_photos(self, user_to_suggest: dict):
        """Данный метод проверяет у найденного пользователя количество
        фотографий в фотографиях профиля, и в случае, когда их больше
        трёх - производит градацию по сумме комментариев и лайков под
        этой фотографии. Затем, отправляется информация о найденном
        пользователе пользователю приложения."""
        params = {
            'owner_id': user_to_suggest['id'],
            'album_id': -6
        }
        profile_album_data = self.user_session.method('photos.get', params)
        media_content = []
        if profile_album_data['count'] <= 3:
            for photo in profile_album_data['items']:
                media_name = f'photo{photo["owner_id"]}_{photo["id"]}'
                media_content.append(media_name)
        else:
            media_content = self.count_photo_metrics(profile_album_data['items'])
        result = ','.join(media_content)
        user_id = self.user_info['id']
        self.write_msg(user_id, 'Мы подобрали Вам пару!')
        self.send_media(user_id=user_id, media_list=result)
        self.write_msg(self.user_info['id'],
                       f'https://vk.com/id{user_to_suggest["id"]}')

    def count_photo_metrics(self, photos: list) -> list:
        """Данный метод получает дополнительную информацию по фотографиям
        альбома профиля найденного пользователя и находит три самые
        популярные фотографии по сумме комментариев и лайков под ними."""
        items = []
        for photo in photos:
            items.append(f'{photo["owner_id"]}_{photo["id"]}')
        params = {
            'photos': ','.join(items),
            'extended': 1
        }
        photos_data = self.user_session.method('photos.getById', params)
        metrics_data = dict()
        for p in photos_data:
            value = p['likes']['count'] + p['comments']['count']
            key = f'photo{p["owner_id"]}_{p["id"]}'
            metrics_data.update({key: value})
        top3 = []
        for _ in range(3):
            max_val = max(metrics_data.values())
            copy_dict = metrics_data.copy()
            for key, value in copy_dict.items():
                if value == max_val and len(top3)<3:
                    top3.append(key)
                    metrics_data.pop(key)
        return top3


if __name__ == '__main__':
    with open('bot_configs.json', 'r') as f:
        bot_configs = json.load(f)
    bot = VKSearchBot(**bot_configs)
    bot.start_listening()
