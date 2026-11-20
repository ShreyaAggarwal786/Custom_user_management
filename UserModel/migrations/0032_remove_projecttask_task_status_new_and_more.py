from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('UserModel', '0031_alter_projecttask_task_status_task_status_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='projecttask',
            name='task_status',
        ),
        migrations.RenameField(
            model_name='projecttask',
            old_name='task_status_new',
            new_name='task_status',
        ),
    ]