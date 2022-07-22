import requests
from os import path
from time import sleep


class YaUploader:
    def __init__(self, token: str):
        self.token = token

    def _is_api_error(self, response_data: dict):
        """Метод проверяет ответ от Yandex Disk API на наличие ошибки и выводит ошибку."""
        if 'error' in response_data:
            raise Exception(
                f'Yandex API {response_data["error"]}: {response_data["description"]}\n' +
                response_data["message"]
            )
        return False

    def _get_upload_link(self, remote_path, overwrite: bool = False):
        """Метод получает ссылку, по которой требуется загрузить файл."""
        endpoint = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
        params = {
            'path': remote_path,
            'overwrite': overwrite
        }
        headers = {'Authorization': f'OAuth {self.token}'}
        response = requests.get(endpoint, headers=headers, params=params)
        data = response.json()
        if not self._is_api_error(data):
            return data.get('href')

    def make_dirs(self, remote_path: str):
        """Метод создает папки и(или) файл по указанному пути remote_path"""
        endpoint = 'https://cloud-api.yandex.net/v1/disk/resources'
        headers = {'Authorization': f'OAuth {self.token}'}
        response = requests.get(endpoint, headers=headers, params={'path': remote_path})
        if response.status_code == 200:
            return True
        path_parts = list(path.split(remote_path))
        current_path = ''
        while path_parts:
            current_path += path_parts.pop(0)
            response = requests.get(endpoint, headers=headers, params={'path': current_path})
            if response.status_code == 200:
                continue
            if response.status_code == 404 and self.make_dir(current_path):
                continue
            self._is_api_error(response.json())
        return True

    def make_dir(self, remote_path):
        """Метод создает файл или папку на Яндекс.Диске по указанному пути remote_path"""
        endpoint = 'https://cloud-api.yandex.net/v1/disk/resources'
        headers = {'Authorization': f'OAuth {self.token}'}
        params = {'path': remote_path}
        response = requests.put(endpoint, headers=headers, params=params)
        if response.status_code == 201:
            return True
        self._is_api_error(response.json())
        return False

    def upload(self, local_path: str, remote_path: str,
               overwrite: bool = False, make_dirs: bool = False, max_retry_count: int = 3):
        """Метод загружает локальный файл на Яндекс.Диск,
        local_path - путь до файла в системе, remote_path - путь до файла на яндекс диске,
        overwrite - перезаписать файл если он уже существует,
        make_dirs - создать все необходимые директории если их нет,
        max_retry_count - количество попыток при ошибках загрузки."""
        if not path.isfile(local_path):
            raise Exception("File to upload not found.")
        if make_dirs:
            self.make_dirs(remote_path)
        endpoint = self._get_upload_link(remote_path, overwrite)
        headers = {
            'Authorization': f'OAuth {self.token}',
            'Content-type': 'application/octet-stream'
        }
        retry_count = 0
        while True:
            response = requests.put(endpoint, headers=headers, data=open(local_path, 'rb'))
            if response.status_code in [201, 202]:
                return True
            if response.status_code == 412:
                raise Exception(
                    'Yandex API error: Precondition Failed\n' +
                    'При дозагрузке файла был передан неверный диапазон в заголовке Content-Range'
                )
            if response.status_code == 413:
                raise Exception('Yandex API error: Payload Too Large\nРазмер файла больше допустимого.')
            if response.status_code == 507:
                raise Exception('Yandex API error: Insufficient Storage\nДля загрузки файла не хватает места на Диске.')
            retry_count += 1
            if retry_count == max_retry_count:
                raise Exception(
                    'File upload error. Exceeded the maximum number of attempts.\n' +
                    f'HTTP STATUS CODE: {response.status_code}'
                )
            sleep(2)


if __name__ == '__main__':
    token = input('Введите токен: ')
    local_path = input('Введите путь к файлу, который нужно загрузить на Яндекс.Диск:\n')
    remote_path = input('Введите путь на Яндекс.Диске где будет сохранен файл:\n')
    overwrite = True if input('Перезаписать файл если он уже существует? Да/Нет: ').lower().startswith('д') else False
    make_dirs = True if input('Создать недостающие папки на Яндекс.Диске? Да/Нет: ').lower().startswith('д') else False
    ya_uploader = YaUploader(token)
    if ya_uploader.upload(local_path, remote_path, overwrite=overwrite, make_dirs=make_dirs):
        print('Файл загружен.')
