from django.contrib import admin
from django.urls import path,include
from app_context import views

urlpatterns = [
    path('',views.homepage, name="home"),
    path('login/',views.login_view, name='login'),
    path('register/',views.register_view, name='register'),
    path('logout/',views.logout_view, name='logout'), 
    # path('input/', views.input, name="inputs"),
    path('input/', views.HookContentView.as_view(), name='inputs'),
    path('processing/<str:task_id>/', views.processing, name="processing"),
    path('processing-successful/<str:task_id>/',views.processingsuccessful, name="processong_successful" ),
    path('merger/', views.merger, name="marger"),
    path('download_all/', views.downloadall, name="download_all"),
    # path('success/', HookContentSuccessView.as_view(), name='hook_content_success'),
    # path('preview/<int:pk>/', HookContentPreviewView.as_view(), name='hook_content_preview'),
    path('delete_temp_files/', views.delete_temp_files, name='delete_temp_files'),
    path('cancel_task/',views.cancel_task,name="cancel_task"),
    path('download_output/',views.download_output,name="download_output"),
]
