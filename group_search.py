import vk_api
import os.path
import fasttext
from conf import conf, group_conf
from dostoevsky.tokenization import RegexTokenizer
from dostoevsky.models import FastTextSocialNetworkModel


class GroupsWall:  # стены сообществ

    def __init__(self):
        session = vk_api.VkApi(token=conf['access_token'])
        self.vk = session.get_api()
        fasttext.FastText.eprint = lambda x: None
        tokenizer = RegexTokenizer()
        self.model = FastTextSocialNetworkModel(tokenizer=tokenizer)
        self.groups = []
        self.can_not = ['|', '"', '/', '\\', ':', '*', '>', '<']
        if not os.path.isdir("groups_wall"):
            os.mkdir("groups_wall")
        for key_group in group_conf:  # поиск сообществ по тегам
            self.get_groups(key_group)  # найти n сообществ по тегу
            self.wall_groups(key_group)  # записать содержимое этих сообществ

    def get_groups(self, key_group):  # поиск n сообществ по тегу
        self.groups = []
        limit = group_conf[key_group]['qty']  # количество сообществ

        if 'key_city' not in group_conf[key_group] or group_conf[key_group]['key_city'] == []:  # фильтр по городам не указан
            groups_id = [ids['id'] for ids in
                         self.vk.groups.search(q=key_group, country_id=1, sort=6, count=limit)['items']]  # список id найденных сообществ
            self.groups_by_id(groups_id, group_conf[key_group]['members_min'])  # информация о сообществе по его id

        else:  # фильтр по городам не указан
            cities = [self.vk.database.getCities(country_id=1, q=city)['items'][0]['id'] for city in group_conf[key_group]['key_city']]

            for city in cities:  # поиск n сообществ из каждого города
                groups_id = [ids['id'] for ids in self.vk.groups.search(q=key_group, city_id=city, sort=6, count=limit)['items']]
                self.groups_by_id(groups_id, group_conf[key_group]['members_min'])

            if len(self.groups) > limit:  # оставить только n самых популярных сообществ из списка городов
                self.groups = sorted(self.groups, key=lambda x: x['members_count'], reverse=True)[:limit]

    def groups_by_id(self, groups, members_min):  # добавление в groups информации о сообществе по его id
        groups = self.vk.groups.getById(group_ids=groups, fields='members_count,description,city')

        for group in groups:
            if group['members_count'] < members_min:
                continue

            self.groups.append({
                'name': group["name"],
                'screen_name': group["screen_name"],
                'description': group["description"],
                'city': group["city"]["title"] if "city" in group else '',
                "members_count": group["members_count"],
                'id': group["id"],
            })

    def wall_groups(self, key_group):  # прочитать и записать стену сообществ по тегу

        if len(self.groups) == 0:  # проверка на наличие записей в сообществе
            return
        if not os.path.isdir(f'groups_wall/{key_group}'):  # создать папку с тегом
            os.mkdir(f'groups_wall/{key_group}')

        for group in self.groups:

            name = f'{group["name"]} ({group["screen_name"]})'  # имя сообщества
            for i in self.can_not:
                name = name.replace(i, ',')
            file = open(f'groups_wall/{key_group}/{name}.txt', 'w', encoding='utf8')  # создать файл
            [file.write(f'{info}: {group[info]}\n') for info in group]
            count = 0

            while count < group_conf[key_group]['count']:  # считать n записей со стены(count)
                wall = self.vk.wall.get(owner_id=-group['id'], count=100, offset=count)['items']  # лимит в 100 записей за раз
                count += 100
                for entry in wall:
                    if entry['text'] == '':  # запись содержит текст
                        continue
                    results = self.model.predict([entry['text']], k=2)
                    results = ', '.join([f'{result}: {"%.3f" % results[0][result]}' for result in results[0]])  # получить тональность текста
                    file.write(f'{"." * 100}\n{entry["text"]}\n{results}\n')  # записать в файл запись + её тональность
            file.close()


if __name__ == '__main__':
    search = GroupsWall()
