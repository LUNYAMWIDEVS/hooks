from django.db import models


class HookContent(models.Model):
    hooks_content = models.FileField(upload_to='hooks_content/')
    google_sheets_link = models.URLField(max_length=1000)
    eleven_labs_api_key = models.CharField(max_length=1000)
    voice_id = models.CharField(max_length=1000)
    task_id = models.CharField(max_length=1000, unique=True)
    main_box_color = models.CharField(max_length=7)  # Hex color code
    font_color = models.CharField(max_length=7)  # Hex color code
    parallel_processing = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def _str_(self):
        return f"Hook Content {self.id}"