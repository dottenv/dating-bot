from tortoise import fields
from tortoise.models import Model

class User(Model):
    id = fields.IntField(pk=True)
    tg_id = fields.BigIntField(unique=True)
    username = fields.CharField(max_length=64, null=True)
    registered_at = fields.DatetimeField(auto_now_add=True)
    is_active = fields.BooleanField(default=True)
    is_premium = fields.BooleanField(default=False)
    is_admin = fields.BooleanField(default=False)
    is_banned = fields.BooleanField(default=False)
    raiting = fields.IntField(default=100)

    # Связь с анкетой 
    profile: fields.ReverseRelation["Profile"]

    def __str__(self):
        return f"User({self.tg_id})"


class Profile(Model):
    id = fields.IntField(pk=True)
    user = fields.OneToOneField("models.User", related_name="profile", on_delete=fields.CASCADE)
    first_name = fields.CharField(max_length=64)
    last_name = fields.CharField(max_length=64, null=True)
    age = fields.IntField(null=True)
    city = fields.CharField(max_length=64, null=True)
    about = fields.TextField(null=True)
    tags = fields.CharField(max_length=256, null=True)  # интересы, можно хранить через запятую
    gender = fields.CharField(max_length=16, null=True)
    orientation = fields.CharField(max_length=32, null=True)
    dating_goal = fields.CharField(max_length=64, null=True)
    photo_id = fields.CharField(max_length=256, null=False)
    profile_completed = fields.BooleanField(default=False)

    def __str__(self):
        return f"Profile({self.first_name}, {self.city})"


class Ban(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="bans", on_delete=fields.CASCADE)
    banned_by = fields.ForeignKeyField("models.User", related_name="issued_bans", on_delete=fields.SET_NULL, null=True)
    ban_type = fields.CharField(max_length=16)  # temp, permanent
    duration_hours = fields.IntField(null=True)  # для временных банов
    reason = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    expires_at = fields.DatetimeField(null=True)  # когда истекает временный бан
    is_active = fields.BooleanField(default=True)
    
    def __str__(self):
        return f"Ban({self.user.tg_id}, {self.ban_type})"


class Advertisement(Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=128)
    text = fields.TextField()
    media_type = fields.CharField(max_length=16, null=True)  # photo, video, document
    media_file_id = fields.CharField(max_length=256, null=True)
    buttons = fields.JSONField(default=list)  # [{"text": "...", "url": "..."}]
    
    # Настройки
    audience = fields.CharField(max_length=16, default="all")  # all, premium, regular
    rounds = fields.IntField(default=1)
    frequency_hours = fields.IntField(default=24)
    
    # Статистика
    total_sent = fields.IntField(default=0)
    total_clicks = fields.IntField(default=0)
    
    # Мета
    created_by = fields.ForeignKeyField("models.User", related_name="ads", on_delete=fields.CASCADE)
    created_at = fields.DatetimeField(auto_now_add=True)
    is_active = fields.BooleanField(default=True)
    
    def __str__(self):
        return f"Ad({self.title})"


class AdClick(Model):
    id = fields.IntField(pk=True)
    ad = fields.ForeignKeyField("models.Advertisement", related_name="clicks", on_delete=fields.CASCADE)
    user = fields.ForeignKeyField("models.User", related_name="ad_clicks", on_delete=fields.CASCADE)
    button_text = fields.CharField(max_length=128)
    clicked_at = fields.DatetimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Click({self.ad.title}, {self.user.tg_id})"


class PremiumPurchase(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="purchases", on_delete=fields.CASCADE)
    stars_amount = fields.IntField()
    duration_days = fields.IntField()
    telegram_payment_id = fields.CharField(max_length=256, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Purchase({self.user.tg_id}, {self.stars_amount} stars)"