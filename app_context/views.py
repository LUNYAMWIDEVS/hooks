from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponse, JsonResponse, FileResponse
from django.core.cache import cache
import glob
import os
import zipfile
import io
import tempfile
import shutil
import signal
from threading import Lock
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from .methods import generate_task_id, process_files
# Create your views here.
from .forms import HookContentForm, LoginForm
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.views import View

upload_tasks = {}
tasks_lock = Lock()
process_pids = {}
canceled_tasks = set()

start_time = datetime.now()

def homepage(request):
    context ={

    }
    return render(request, 'app_context/homepage.html', context)

def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
        return redirect('home')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        email = request.POST.get('username')
        password = request.POST.get('password')
        print('-------------')
        print(email, password)
        user = authenticate(request, username=email, password=password)
        print('user ->', user)
        if user is not None:
            login(request, user)
        form = LoginForm(request, data=request.POST)
        # import pdb;pdb.set_trace()
        if form.is_valid():
            email = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('inputs') 
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Invalid form input.')
            
    else:
        form = LoginForm()
    return render(request, 'app_context/loginpage.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        if password == password2:
            if User.objects.filter(username=email).exists():
                messages.error(request, 'Email is already taken.')
            else:
                user = User.objects.create_user(username=email, email=email, password=password)
                user.save()
                messages.success(request, 'Account created successfully.')
                return redirect('login')
        else:
            messages.error(request, 'Passwords do not match.')
    return render(request, 'app_context/registerpage.html')

# def input(request):
#     return render(request, 'app_context/inputpage.html')

class HookContentView(View):
    def get(self, request):
        form = HookContentForm()
        return render(request, 'app_context/inputpage.html', {'form': form})

    def post(self, request):
        task_id = generate_task_id()
        parallel_processing = True, #1
        print(task_id)

        # Create a mutable copy of the POST data
        post_data = request.POST.copy()
        post_data['task_id'] = task_id  # Add the task_id to the form data
        post_data['parallel_processing'] = parallel_processing  # Add the task_id to the form data

        print('request post', request.POST, post_data)
        # Pass the modified POST data to the form
        form = HookContentForm(post_data, request.FILES)
        # print('form 11 ->', form)
        # import pdb;pdb.set_trace()
        if form.is_valid():
            form.save()
            # print(form)
            return redirect('processing', task_id=task_id)

        print('forms error ->', form.errors)
        return render(request, 'app_context/inputpage.html', {'form': form})


def processing(request, task_id):
    print('task_id ->', task_id)
    temp_dir = tempfile.mkdtemp(prefix=f"task_{task_id}_")
    print('temp_dir ->', temp_dir)
    # import pdb;pdb.set_trace()
    data = process_files(temp_dir, task_id)
    # return render(request, 'app_context/processingpage.html')
    return redirect('processong_successful')

@csrf_exempt
def processingsuccessful(request):
    return render(request, 'app_context/processing_successful.html')

def merger(request):
    return render(request, 'app_context/mergerpage.html')

@csrf_exempt
def downloadall(request):
    

    try:
        # Get the task ID from the request
        post_data = request.POST.copy()
        task_id = post_data.get('task_id')
        if not task_id:
            return JsonResponse({"error": "Task ID is required"}, status=400)
            # messages.error(request, 'Task ID is required')
            # return jsonify({"error": "Task ID is required"}), 400
        temp_dir = cache.get(task_id)
        # Define the output folder where the videos are stored based on the task_id
        output_videos_folder = f"/tmp/task_{task_id}_*/output/videos"
        output_videos_folder = "/var/folders/s3/t33pq9yn2jj0yqnk4jkrt2jn4g8cft/T/task_task-iw3GDoCk4_jzs9tw0m/output/videos"

        # Glob to match the task folder that may have random suffixes
        matching_folders = glob.glob(output_videos_folder)
        if not matching_folders:
            # messages.error(request, 'Output videos folder not found')
            return JsonResponse({"error": "Output videos folder not found"}, status=400)
            # return jsonify({"error": "Output videos folder not found"}), 400
        
        # Assuming there's only one matching folder
        output_videos_folder = matching_folders[0]

        # List the video files in the output folder
        video_files = [f for f in os.listdir(output_videos_folder) if f.endswith('.mp4') or f.endswith('.mov')]
        if not video_files:
            return JsonResponse({"error": "No video files found to zip"}, status=400)

        # Create a zip file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            for video_file in video_files:
                video_path = os.path.join(output_videos_folder, video_file)
                zip_file.write(video_path, os.path.basename(video_path))

        # Prepare the zip file for download
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename=videos_'+ task_id + '.zip'
        return response
        # return send_file(
        #     zip_buffer,
        #     mimetype='application/zip',
        #     as_attachment=True,
        #     download_name=f'videos_{task_id}.zip'
        # )
    except Exception as e:
        print(f"Error during zip creation: {str(e)}")
        return  JsonResponse({"error": str(e)}, status=500)
    

# @csrf_exempt
# def downloadall(request):
    # try:
    #     # Get the task ID from the request
    #     task_id = request.POST.get('task_id')
    #     if not task_id:
    #         return JsonResponse({"error": "Task ID is required"}, status=400)
    #     output_videos_folder = "/var/folders/s3/t33pq9yn2jj0yqnk4jkrt2jn4g8cft/T/task_task-iw3GDoCk4_jzs9tw0m/output/videos"

    #     # Get the temp_dir from cache (assuming it's stored there)
    #     # temp_dir = cache.get(task_id)
    #     # if not temp_dir:
    #     #     return JsonResponse({"error": "Task not found"}, status=400)

    #     # Define the output folder where the videos are stored
    #     # output_videos_folder = os.path.join(temp_dir, "output", "videos")

    #     # Check if the folder exists
    #     if not os.path.exists(output_videos_folder):
    #         return JsonResponse({"error": "Output videos folder not found"}, status=400)

    #     # List the video files in the output folder
    #     video_files = [f for f in os.listdir(output_videos_folder) if f.endswith(('.mp4', '.mov'))]
    #     if not video_files:
    #         return JsonResponse({"error": "No video files found to zip"}, status=400)

    #     # Create a zip file in memory
    #     zip_buffer = io.BytesIO()
    #     with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
    #         for video_file in video_files:
    #             video_path = os.path.join(output_videos_folder, video_file)
    #             zip_file.write(video_path, os.path.basename(video_path))

    #     # Prepare the zip file for download
    #     zip_buffer.seek(0)
    #     response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    #     response['Content-Disposition'] = f'attachment; filename=videos_{task_id}.zip'
    #     return response

    # except Exception as e:
    #     print(f"Error during zip creation: {str(e)}")
    #     return JsonResponse({"error": str(e)}, status=500)



@csrf_exempt
def delete_temp_files(request):
    if request.method == 'POST':
        try:
            # Delete files in /tmp
            tmp_files = glob.glob('/tmp/*')
            for file_path in tmp_files:
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except PermissionError:
                    print(f"Permission denied: {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {str(e)}")

            # Delete files in /var/tmp
            var_tmp_files = glob.glob('/var/tmp/*')
            for file_path in var_tmp_files:
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except PermissionError:
                    print(f"Permission denied: {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {str(e)}")

            return render(request, 'app_context/delete_temp_files.html', {'message': 'Temporary files deleted successfully'})
        except Exception as e:
            return render(request, 'app_context/delete_temp_files.html', {'error': str(e)})
    else:
        return render(request, 'app_context/delete_temp_files.html', {'error': 'Invalid request method'})

@csrf_exempt
def cancel_task(request):
    if request.method == 'POST':
        try:
            task_id = request.json.get('task_id')
            print(f"Received request to cancel task: {task_id}")
            with tasks_lock:
                if task_id in canceled_tasks:
                    print(f"Task {task_id} already marked for cancellation")
                canceled_tasks.add(task_id)
                if task_id in upload_tasks:
                    upload_tasks[task_id] is False
                    for pid in process_pids.get(task_id, []):
                        try:
                            os.kill(pid, signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                    process_pids.pop(task_id, None)
                    print(f"Task {task_id} set to be canceled")
            return render(request, 'app_context/cancel_task.html', {"message": "Task cancellation request processed"})
        except Exception as e:
            print(f"Error handling cancel task request: {e}")
            return render(request, 'app_context/cancel_task.html', {'error': str(e)})
    else:
        return render(request, 'app_context/cancel_task.html', {'error': 'Invalid request method'})
    


@csrf_exempt
def download_output(request):
    video_path = request.GET.get('video_path')
    if video_path and os.path.exists(video_path):
        print("Debug: File exists, sending file")
        response = FileResponse(open(video_path, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(video_path)}"'
        return response
    else:
        print("Debug: File not found")
        return JsonResponse({"error": "File not found"}, status=404)
