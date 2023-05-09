import requests
import datetime
import json
from tqdm import tqdm
import configparser


def read_token_id(from_file):
    """
    Функция чтения
    токена и ID пользователя
    из файла
    """
    config = configparser.ConfigParser()
    config.read(from_file)
    token = config["TOKEN"]["token"]
    user_id = config["TOKEN"]["user_id"]
    return [token, user_id]



def find_photo_max_size(search_from_user):
    """
    Функция возврата
    ссылки на фотографию
    максимального размера
    и размер фотографии
    """
    max_size = 0
    found = 0
    for i in range(len(search_from_user)):
        photo_size = search_from_user[i].get('width') * search_from_user[i].get('height')
        if photo_size > max_size:
            max_size = photo_size
            found = i
    return search_from_user[found].get('url'), search_from_user[found].get('type')


def to_normal_format(date_time):
    """
    Функция преобразования
    даты загрузки фотографии
    в обычный формат
    """
    origin_format = datetime.datetime.fromtimestamp(date_time)
    converted = origin_format.strftime('%Y-%m-%d time %H-%M-%S')
    return converted


class VkUser:
    def __init__(self, token_list, version='5.131'):
        """
        Метод получения начальных параметров
        запроса для VK
        """
        self.token = token_list[0]
        self.id = token_list[1]
        self.version = version
        self.start_params = {'access_token': self.token, 'v': self.version}
        self.json, self.export_dict = self._sort_info()

    def _get_photos(self):
        """
        Метод получения
        фотографий по
        параметрам
        """
        url = 'https://api.vk.com/method/photos.get'
        params = {'owner_id': self.id,
                  'album_id': 'wall',
                  'photo_sizes': 1,
                  'extended': 1,
                  'rev': 1
                  }
        photos_params = requests.get(url, params={**self.start_params, **params}).json()['response']
        return photos_params['count'], photos_params['items']

    def _get_photo_params(self):
        """
        Метод получения
        параметров
        фотографий
        """
        photo_count, photo_options = self._get_photos()
        result = {}
        for i in range(photo_count):
            likes_count = photo_options[i]['likes']['count']
            url_download, picture_size = find_photo_max_size(photo_options[i]['sizes'])
            time_warp = to_normal_format(photo_options[i]['date'])
            get_value = result.get(likes_count, [])
            get_value.append({'likes_count': likes_count,
                              'add_name': time_warp,
                              'url_picture': url_download,
                              'size': picture_size})
            result[likes_count] = get_value
        return result

    def _sort_info(self):
        """
        Метод получения словаря
        с параметрами фотографий
        и списка JSON для выгрузки
        """
        json_list = []
        sorted_dict = {}
        picture_dict = self._get_photo_params()
        counter = 0
        for elem in picture_dict.keys():
            for value in picture_dict[elem]:
                if len(picture_dict[elem]) == 1:
                    file_name = f'{value["likes_count"]}.jpeg'
                else:
                    file_name = f'{value["likes_count"]} {value["add_name"]}.jpeg'
                json_list.append({'file name': file_name, 'size': value["size"]})
                if value["likes_count"] == 0:
                    sorted_dict[file_name] = picture_dict[elem][counter]['url_picture']
                    counter += 1
                else:
                    sorted_dict[file_name] = picture_dict[elem][0]['url_picture']
        return json_list, sorted_dict


class YandexDisk:
    def __init__(self, folder_name, token_list, num=5):
        """
        Метод получения
        основных параметров
        для загрузки фотографий
        """
        self.token = token_list[0]
        self.added_files_num = num
        self.url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
        self.headers = {'Authorization': self.token}
        self.folder = self._create_folder(folder_name)

    def _create_folder(self, folder_name):
        """
        Метод создания
        папки на YandexDisk
        для загрузки фотографий
        """
        url = "https://cloud-api.yandex.net/v1/disk/resources"
        params = {'path': folder_name}
        if requests.get(url, headers=self.headers, params=params).status_code != 200:
            requests.put(url, headers=self.headers, params=params)
            print(f'\nПапка {folder_name} успешно создана в корневом каталоге YandexDisk\n')
        else:
            print(f'\nПапка {folder_name} уже существует! Файлы с одинаковыми именами не будут скопированы\n')
        return folder_name

    def _in_folder(self, folder_name):
        """
        Метод получения
        ссылки для загрузки
        фотографий на YandexDisk
        """
        url = "https://cloud-api.yandex.net/v1/disk/resources"
        params = {'path': folder_name}
        resource = requests.get(url, headers=self.headers, params=params).json()['_embedded']['items']
        in_folder_list = []
        for elem in resource:
            in_folder_list.append(elem['name'])
        return in_folder_list

    def create_copy(self, dict_files):
        """
        Метод загрузки
        фотографий на YandexDisk
        """
        files_in_folder = self._in_folder(self.folder)
        copy_counter = 0
        for key, i in zip(dict_files.keys(), tqdm(range(self.added_files_num))):
            if copy_counter < self.added_files_num:
                if key not in files_in_folder:
                    params = {'path': f'{self.folder}/{key}',
                              'url': dict_files[key],
                              'overwrite': 'false'}
                    requests.post(self.url, headers=self.headers, params=params)
                    copy_counter += 1
                else:
                    print(f'Предупреждение: файл {key} уже существует!')
            else:
                break

        print(f'\nРезервная копия успешно создана. Новых файлов заружено: {copy_counter}'
              f'\nВсего файлов в исходном альбоме VK: {len(dict_files)}')


if __name__ == '__main__':

    TOKEN_VK = 'vk_settings.ini'
    TOKEN_YA = 'ua_settings.ini'
    # Получение JSON списка с информацией о фотографииях
    VK_list = VkUser(read_token_id(TOKEN_VK))
    # Сохранение JSON списка в файл VK_backups.json
    with open('VK_backups.json', 'w') as outfile:
        json.dump(VK_list.json, outfile)

    # Создаем экземпляр класса YandexDisk с параметрами: "Имя папки", "Токен" и количество скачиваемых файлов
    send_to_yandex = YandexDisk('VK backups', read_token_id(TOKEN_YA), 5)

    # Вызываем метод create_copy для копирования фотографий с VK на Я-диск
    send_to_yandex.create_copy(VK_list.export_dict)
