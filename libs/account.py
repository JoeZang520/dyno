import json
import os
from datetime import datetime

from libs.db import DB


class Account:
    def __init__(self):
        init_sql = """
                CREATE TABLE IF NOT EXISTS account (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    user_no TEXT NOT NULL,
                    user_name NULL,
                    email NULL,
                    twitter NULL,
                    discord NULL,
                    is_vip BOOLEAN DEFAULT FALSE,
                    vip_expire_date TEXT NULL,
                    fee_rate DECIMAL NULL,
                    rep INTEGER NULL,
                    config TEXT NULL,
                    status INTEGER DEFAULT 0,
                    last_update DATETIME NULL,
                    remark TEXT NULL
                )
                """
        DB().run_sql(init_sql)
        self.accounts = self.load_all()
        if len(self.accounts.keys()) == 0:
            self.init_from_env()
            self.accounts = self.load_all()

    @staticmethod
    def reset():
        DB().run_sql("DROP TABLE account")

    def init_from_env(self):
        user_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../.env')
        with open(user_data_path, 'r') as f:
            env = json.load(f)

        existing_accounts = self.accounts

        accounts = env.get('accounts')
        db = DB()
        for user_id in existing_accounts:
            if user_id not in accounts:
                # 删除数据
                sql = """
                DELETE from account WHERE user_id = ? 
                """
                db.run_sql(sql, (user_id,))

        for user_id in accounts:
            account = accounts.get(user_id)
            user_no = account.get('user_id')
            if 'user_id' in account:
                del account['user_id']
            if 'is_vip' in account:
                del account['is_vip']

            if user_id in existing_accounts:
                # 更新数据
                sql = """
                UPDATE account set user_no=?, config=?
                WHERE user_id = ? 
                """
                db.run_sql(sql, (
                    user_no,
                    json.dumps(account),
                    user_id
                ))
            else:
                # 插入
                sql = """
                    INSERT INTO account (user_id, user_no, config, status, remark)
                    VALUES(?,?,?,?,?)
                """
                db.run_sql(sql, (
                    user_id,
                    user_no,
                    json.dumps(account),
                    1,
                    ''
                ))

    def load_all(self):
        sql = """
        SELECT user_id, user_no, user_name, is_vip, vip_expire_date, fee_rate, rep, config, status, remark ,
        last_update
        FROM account
        """
        rows = DB().fetch_all(sql)
        accounts = {}
        for row in rows:
            user_id = str(row[0])
            user_no = row[1]
            user_name = row[2]
            is_vip = row[3]
            vip_expire_date = row[4]
            fee_rate = row[5]
            rep = row[6]
            config = json.loads(row[7])
            status = row[8]
            remark = row[9]
            account = {
                'user_id': user_id,
                'user_no': user_no,
                'user_name': user_name,
                'is_vip': is_vip,
                'vip_expire_date': vip_expire_date,
                'fee_rate': fee_rate,
                'rep': rep,
                'status': status,
                'remark': remark,
                'last_update': row[10]
            }
            for key in config:
                account[key] = config.get(key)
            accounts[user_id] = account
        return accounts

    def get(self, user_id):
        return self.accounts.get(str(user_id), {})

    def save_fee_rate(self, user_id, fee_rate):
        sql = """
        UPDATE account set fee_rate=?
        WHERE user_id = ?
        """
        DB().run_sql(sql, (fee_rate, user_id))

    def save_user_info(self, user_id, user_name, is_vip, vip_expire_date):
        sql = """
                UPDATE account set user_name=?, is_vip = ?, vip_expire_date = ?, last_update = ?
                WHERE user_id = ?
                """
        datetime_format = '%Y-%m-%d %H:%M:%S'
        if not is_vip:
            vip_expire_date = ''
        DB().run_sql(sql, (
            user_name,
            is_vip,
            vip_expire_date,
            datetime.now().strftime(datetime_format),
            user_id
        ))

    def save_email(self, user_id, email):
        sql = """
                UPDATE account set email=? WHERE user_id = ?
                """
        DB().run_sql(sql, (
            email,
            user_id
        ))

    def save_twitter(self, user_id, twitter):
        sql = """
                UPDATE account set twitter=? WHERE user_id = ?
                """
        DB().run_sql(sql, (
            twitter,
            user_id
        ))

    def save_discord(self, user_id, discord):
        sql = """
                UPDATE account set discord=? WHERE user_id = ?
                """
        DB().run_sql(sql, (
            discord,
            user_id
        ))
