from django.db import migrations

BIOGRAPHY_TEXT = """Мене звати Олександра Ярош, і я - професійна фотографка

Взаємодіючи зі світом, я завжди прагнула почути, розгадати та пізнати людей глибше. Це спонукало мене досліджувати мистецтво фотографії, де я можу перетворити своє бачення на візуальну історію, зупиняючи найцінніші моменти у кадрі

Для мене фотографія - це завжди про людину та атмосферу
Тому кожна наша співпраця будується не лише на моєму професійному досвіді, але й на стовідсотковій залученості, щирій увазі та бажанні показати вашу справжність"""


def create_biography(apps, schema_editor):
    Biography = apps.get_model("yarosh_website", "Biography")
    if not Biography.objects.exists():
        Biography.objects.create(title="ПРО МЕНЕ", text=BIOGRAPHY_TEXT)


def delete_biography(apps, schema_editor):
    Biography = apps.get_model("yarosh_website", "Biography")
    Biography.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("yarosh_website", "0008_biography"),
    ]

    operations = [
        migrations.RunPython(create_biography, delete_biography),
    ]
