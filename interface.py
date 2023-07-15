# импорты
import vk_api
from sqlalchemy import create_engine
from vk_api.longpoll import VkEventType, VkLongPoll
from vk_api.utils import get_random_id

from config import acces_token, comunity_token, db_url_object
from core import VkTools
from data_store import Base, add_user, check_user

class BotInterface():
    def __init__(self, comunity_token, acces_token, engine):
        self.vk = vk_api.VkApi(token=comunity_token)
        self.longpoll = VkLongPoll(self.vk)
        self.vk_tools = VkTools(acces_token)
        self.engine = engine
        self.params = {}
        self.worksheets = []
        self.offset = 0


    def message_send(self, user_id, message, attachment=None):
        self.vk.method('messages.send', {'user_id': user_id,
                        'message': message,
                        'attachment': attachment,
                        'random_id': get_random_id()}
                       )

    def event_handler(self):
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                if not self.params:
                    self.params = self.vk_tools.get_profile_info(event.user_id)
                    command = event.text.lower()
                    # список команд продублирован в приветствии бота в ВК
                    # 1 запрос - первый запрос пользователя
                    if command == 'привет' or command == 'старт' or command == 'начать' or command == 'пуск':
                        self.message_send(event.user_id, f'Здравствуй, {self.params["name"]}. \n Я помогу тебе найти идеальную пару ВКонтакте. \n Для общения со мной нужно использовать специальные команды, список команд можно получить, написав слово команды.')
                    # 2 запрос - список команд
                    elif command == 'команды' or command == 'команда':
                        self.message_send(event.user_id, 'Вот список команд для работы со мной: \n бот- запускаем работу и анализиуем твой профиль \n показать анкету - показываем подходящие анкеты \n следующая - листаем анкеты \n завершить - завершение работы бота')
                    # 3 запрос - запускаем бота и проверяем профиль, запашиваем неизвестные данные
                    elif command == 'бот':
                        self.message_send(event.user_id, 'Запускаю работу и анализирую твой профиль.')
                        if self.params.get("city") is None:
                            self.message_send(event.user_id, 'Укажите Ваш город в формате "город <название>"\n например "город Москва".')
                            continue
                        elif self.params.get("bdate") is None:
                            self.message_send(event.user_id, 'Укажите Ваш возраст в формате "возраст <число>"\n например "возраст 18".')
                            continue
                        else:
                            self.message_send(event.user_id, 'Город и возраст записали из твоей анкеты.\n Для просмотра анкет напиши команду показать анкеты')
                    # 4 запрос - если нет города
                    elif command.startswith("город "):
                        city_name = ' '.join(event.text.lower().split()[1:])
                        city = self.vk_tools.__class__(city_name)
                        if city is None:
                            self.message_send(event.user_id, 'Не удалось найти такой город')
                        else:
                            self.params['city'] = self.vk_tools.__class__(city_name)
                            self.message_send(event.user_id, f'Вы успешно установили город.\n Для просмотра анкет напиши команду показать анкеты')
                    # 5 запрос - если нет возраста, то есть года в профиле
                    elif command.startswith("возраст "):
                        age = event.text.lower().split()[1]
                        try:
                            age = int(age)
                        except ValueError:
                            self.message_send(event.user_id, 'Необходимо ввести число')
                            continue
                        if not 18 <= age <= 99:
                            self.message_send(event.user_id, 'Ваш возраст должен быть от 18 до 99 лет')
                            continue
                        self.params['bdate'] = age
                        self.message_send(event.user_id, 'Вы успешно установили свой возраст.\n Для просмотра анкет напиши команду показать анкеты')
                    #6 запрос - запускаем анкеты
                    elif command == 'показать анкеты' or command == 'показать анкету':
                        # логика поиска анкет
                        worksheet = self.worksheets.pop()
                        if not self.worksheets:
                            self.worksheets = self.vk_tools.search_worksheet(self.params, self.offset)
                        # логика фото
                            photos = self.vk_tools.get_photos(worksheet['id'])
                            photo_string = ''
                            for photo in photos:
                                photo_string += f'photo{photo["owner_id"]}_{photo["id"]},'
                            self.offset += 1
                            # показываем первую анкету пользователю
                            self.message_send(event.user_id, f'имя: {worksheet["name"]} ссылка: vk.com/id{worksheet["id"]}',
                                attachment=photo_string
                            )
                            # добавляем эту анкету в БД
                            add_user(self.engine, event.user_id, worksheet['id'])
                        # так как это первая анкета, мы не проверяем ее в БД, а просто запишем
                        else:
                            # для IF пропишем обязательный ELSE или ELIF, например ...
                            # если есть какие то анкеты, то добавляем их в БД
                            add_user(self.engine, event.user_id, worksheet['id'])
                    # 7 запрос - листаем анкеты
                    elif command == 'следующая':
                        # так как это не первая анкета, мы будем проверять ее в БД + записывать в БД
                        def get_profile(self, worksheets, event):
                            while True:
                                if worksheets:
                                    #проверка анкеты в БД
                                    if not check_user(engine, event.user_id, worksheet['id']):
                                        #добавить анкету в БД
                                        add_user(engine, event.user_id, worksheet['id'])
                                    yield worksheet
                                else:
                                    worksheet = worksheets.pop()
                                    worksheets = self.vk_tools.search_worksheet(self.params, self.offset)
                                    # логика поиска анкет
                                    if not self.worksheets:
                                        self.worksheets = self.vk_tools.search_worksheet(self.params, self.offset)
                                    # логика фото
                                    photos = self.vk_tools.get_photos(worksheet['id'])
                                    photo_string = ''
                                    for photo in photos:
                                        photo_string += f'photo{photo["owner_id"]}_{photo["id"]},'
                                    self.offset += 1
                                    # показываем следующую анкету пользователю
                                    self.message_send(event.user_id,
                                                      f'имя: {worksheet["name"]} ссылка: vk.com/id{worksheet["id"]}',
                                                      attachment=photo_string
                                                      )
                                    add_user(self.engine, event.user_id, worksheet['id'])
                    # 8 запрос - завершение клиентом
                    elif command == 'пока' or command == "нет" or command == "стоп" or command == "завершить" or command == "закончить" or command == "конец":
                        self.message_send(event.user_id, 'Завершаю работу, тебе спасибо за внимание, буду рад видеть снова.')
                    # 9 запрос - все остальное
                    else:
                        self.message_send(event.user_id, 'Для общения со мной нужно использовать специальные команды. Список команд для обшения со мной можно получить написав слово команды.')


if __name__ == '__main__':
    engine = create_engine(db_url_object)
    Base.metadata.create_all(engine)
    bot_interface = BotInterface(comunity_token, acces_token, engine)
    bot_interface.event_handler()

