# импорты
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
from config import comunity_token, acces_token, db_url_object
from core import VkTools
from data_store import add_user, check_user
from sqlalchemy import create_engine

class BotInterface:
    def __init__(self, comunity_token, acces_token):
        self.interface = vk_api.VkApi(token=comunity_token)
        self.vk_tools = VkTools(acces_token)
        self.api = VkTools(acces_token)
        self.params = None
        self.worksheets = []
        self.offset = 0

    def message_send(self, user_id, message, attachment=None):
        self.interface.method('messages.send',
                       {'user_id': user_id,
                        'message': message,
                        'attachment': attachment,
                        'random_id': get_random_id()}
                       )

    def event_handler(self):
        longpoll = VkLongPoll(self.interface)

        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                command = event.text.lower()
                if command == 'привет':
                    self.params = self.api.get_profile_info(event.user_id)
                    self.message_send(event.user_id, f'Здравствуй {self.params["name"]}')
                        if not self.params['city'] and not self.params['bdate']:
                            self.message_send(event.user_id, 'Проверка данных...')
                        elif not self.params['city']:
                            self.message_send(event.user_id, f"{self.params['name']}, введите ваш город")
                        city = event.text.lower()
                        self.message_send(event.user_id, city)
                        self.params['city'] = city.capitalize()
                    elif self.params['city']:
                        self.message_send(event.user_id, f"{self.params['name']}, у Вас уже введён город")
                        if not self.params['bdate']:
                            self.message_send(event.user_id, f"{self.params['name']}, введите Вашу дату рождения")
                            bdate = event.text
                            self.message_send(event.user_id, bdate)
                            self.params['bdate'] = bdate
                    elif self.params['bdate']:
                        self.message_send(event.user_id, f"{self.params['name']}, у Вас уже введена дата рождения")
                elif command == 'поиск':
                    self.message_send(
                        event.user_id, 'Начинаем поиск')
                    if self.worksheets:
                        worksheet = self.worksheets.pop()
                        photos = self.vk_tools.get_photos(worksheet['id'])
                        photo_string = ''
                        for photo in photos:
                            photo_string += f'photo{photo["owner_id"]}{photo["id"]}'
                    else:
                        self.worksheets = self.vk_tools.search_worksheet(
                            self.params, self.offset)
                        worksheet = self.worksheets.pop()
                        photos = self.vk_tools.get_photos(worksheet['id'])
                        photo_string = ''
                        for photo in photos:
                            photo_string += f'photo{photo["owner_id"]}_{photo["id"]},'
                        self.offset += 10
                    self.message_send(
                        event.user_id,
                        f'имя: {worksheet["name"]} ссылка: vk.com/{worksheet["id"]}',
                        attachment=photo_string
                    )
                    if not check_user(engine, event.user_id, worksheet["id"]):
                        add_user(engine, event.user_id, worksheet["id"])
                elif command == 'пока':
                    self.message_send(event.user_id, 'До новых встреч')
                else:
                    self.message_send(event.user_id, 'Вы ввели неизвестную команду')

if __name__ == '__main__':
    engine = create_engine(db_url_object)
    bot_interface = BotInterface(comunity_token, acces_token)
    bot_interface.event_handler()

