from rest_framework import viewsets
from BugTracker.serializers import *
from BugTracker.models import *
from BugTracker.permissions import *
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
import requests
from django.contrib.auth import login, logout
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
#from django.middleware import csrf;
# Create your views here.

# View for displaying the AppUser Content
class AppUserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AppUser.objects.all()
    serializer_class = AppUserSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        instance.delete()

    @action(methods=['get', ], detail=False, url_name='onlogin', url_path='onlogin', permission_classes=[AllowAny])
    def on_login(self, request):
        code = request.GET.get('code')
        print(code)
        #GETTING THE AUTHORISATION CODE
        
        url = 'https://internet.channeli.in/open_auth/token/'
        data = {
                'client_id':'gfZHj4O7eZKrzv8Vpgqi1s5kKWgvgyFCf5vt822c',
                'client_secret':'0DTRwGP07h4r4gF7IUGdEvpw6jp9mvk7hYchwDldW1PjnqvbhBacIFXBeFSA0etDI8CBouTGeJb42t9hEOhraSXcRWkUrSZ2bidOjawPD4QZBCGiuZV0F4emsGSmYxMz',
                'grant_type':'authorization_code',
                'redirect_url':'http://127.0.0.1:8000/appusers/onlogin',
                'code': code
                } 
        
        user_data = requests.post(url=url, data=data).json()
        print(user_data)
        acs_token = user_data['access_token']
        #print(acs_token)
        
        #GET ACCESS TOKEN
        
        headers={
                'Authorization':'Bearer ' + acs_token
                }
        user_data = requests.get(url='https://internet.channeli.in/open_auth/get_user_data/', headers=headers)
        #return HttpResponse(user_data)
        
        #CHECK IF USER EXISTS
        print(user_data.json())
        try:
            user_data = user_data.json()
            user = AppUser.objects.get(enrNo=user_data["student"]["enrolmentNumber"])
            print(user_data['person']['displayPicture'])
        except AppUser.DoesNotExist:
            #CHECK IMG MEMBER OR NOT
            in_img = False
            for role in user_data["person"]["roles"]:
                
                if role["role"] == "Maintainer":
                    in_img = True
                    break
            
            if in_img:
                enrNum = user_data["student"]["enrolmentNumber"]
                email = user_data["contactInformation"]["instituteWebmailAddress"]
                dp = user_data['person']['displayPicture']

                name = (user_data["person"]["fullName"]).split()
                firstname = name[0]
                fullName = user_data["person"]["fullName"]

                user_role_assigned = 1
                if user_data['student']['currentYear'] >= 2:
                    user_role_assigned = 2

                newUser = AppUser(enrNo = enrNum, email=email, first_name = firstname, username=fullName, user_role = user_role_assigned, access_token = acs_token, display_picture = dp)
                newUser.is_staff = True
                newUser.save()
                login(request, newUser)

                return Response({'status': 'User Created', 'access_token': acs_token}, status=status.HTTP_202_ACCEPTED)
            else:
                return Response({'status': 'User not in IMG'}, status=status.HTTP_401_UNAUTHORIZED)
        user.access_token = acs_token
        user.display_picture = user_data['person']['displayPicture']
        user.save()
        login(request, user)
        return Response({'Status': 'User Exists', 'access_token': acs_token})

    @action(methods = ['get','options'], detail=False, url_path='current_user', url_name='current_user', permission_classes=[AllowAny])
    def get_current_user_data(self, request):
        if request.user.is_authenticated:
            ser = AppUserSerializer(request.user)
            return Response(ser.data, status=status.HTTP_202_ACCEPTED)
        else:
            return Response({'Response':'No Current User'})

    @action(methods=['get', 'options',], detail=False, url_name='test', url_path='test', permission_classes=[AllowAny])
    def test(self, request):
        if request.user.is_authenticated:
            ser = AppUserSerializer(request.user)
            return Response(ser.data, status=status.HTTP_202_ACCEPTED)
        else:
            print(request.user)
            return Response({"enrollment_number": 'Not authenticated'})

    @action(methods = ['get', 'options',], detail=False, url_path='my_page', url_name='my_page', permission_classes=[AllowAny])
    def get_my_page(self, request):
        code = request.GET.get('code')
        user = AppUser.objects.get(access_token = code)
        serializer = AppUserSerializer(user)
        login(request=request, user=user)

        user_projects = Project.objects.filter(members=user.pk)
        serializer2 = ProjectGETSerializer(user_projects, many=True)

        user_assigned_issues = Issues.objects.filter(assigned_to=user.pk)
        serializer3 = IssueGETSerializer(user_assigned_issues, many=True)

        user_reported_issues = Issues.objects.filter(reported_by=user.pk)
        serializer4 = IssueGETSerializer(user_reported_issues, many=True)
        
        return Response({'user_data': serializer.data,
                         'projects': serializer2.data,
                         'assigned_issues': serializer3.data,
                         'reported_issues': serializer4.data})

    
    @action(methods = ['get',], detail=True, url_path='user_info', url_name='user_info', permission_classes=[AllowAny])
    def get_user_info(self, request, pk):
        user = AppUser.objects.get(pk=pk)
        user_projects = Project.objects.filter(members=user.pk)
        serializer = AppUserSerializer(user)
        serializer2 = ProjectGETSerializer(user_projects, many=True)
        user_reported_issues = Issues.objects.filter(reported_by=user.pk)
        serializer3 = IssueGETSerializer(user_reported_issues, many=True)
        return Response({"user_details": serializer.data,
                         "project": serializer2.data,
                         "issues_reported": serializer3.data})

    @action(methods = ['get',], detail = True, url_path='convert_role', url_name='convert_role')
    def convert_user_role(self, request, pk):
        user = AppUser.objects.get(pk=pk)
        user.user_role = request.GET.get('new_role')
        user.save()
        return Response({'status': 'Status Changed'})

    @action(methods = ['get',], detail=True, url_path='disable_user', url_name='disable_user')
    def disable_user(self, request, pk):
        user = AppUser.objects.get(pk = pk)
        user.is_disabled = request.GET.get('is_disabled')
        user.save()
        return Response({'status': 'User Status Changed'})

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProjectPOSTSerializer
        else:
            return ProjectGETSerializer

    @action(methods=['get', ], detail=True, url_path='issues', url_name='issues')
    def get_issues(self, request, pk):
        try:
            issues_list = Issues.objects.filter(project=pk)
        except KeyError:
            return Response({'Empty': 'No Issues for this project yet'}, status = status.HTTP_204_NO_CONTENT)

        ser = IssueGETSerializer(issues_list, many=True)
        return Response(ser.data)

    #@permission_classes(IsAdminOrProjectCreator)
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
        except Http404:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['get', 'options'], detail=False, url_path='add_project', url_name='add_path')
    def add_project(self, request):
        if request.user.is_authenticated:
            code = request.GET
            name = request.GET.get('name')
            wiki = request.GET.get('wiki')
            status = request.GET.get('status')
            creator = request.GET.get('creator')
            members = []
            for x in range(len(code) - 4):
                members.append(request.GET.get('members[%d]' % x))
            creator_user = AppUser.objects.get(pk = creator)
            team_members = []
            for m in members:
                team_members.append(AppUser.objects.get(pk = m))
            newProject = Project(name = name, wiki = wiki, status = status, creator = creator_user)
            newProject.save()
            newProject.members.set(team_members)
            return Response({'Response':'Project Created'})
        else:
            return Response({'Response':'User Not Authenticated.'})

class IssuesViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        try:
            return Issues.objects.filter(project=self.kwargs['project_pk'])
        except:
            try:
                return Issues.objects.filter(assigned_to=self.kwargs['assigned_to_pk'])
            except KeyError:
                try:
                    return Issues.objects.filter(reported_by=self.kwargs['reported_by_pk'])
                except KeyError:
                    return Issues.objects.all()
    queryset = Issues.objects.all()

    @action(methods=['patch', 'get'], detail=True, url_path='assign', url_name='assign')
    def assign_issue(self, request, pk):
        assign_to = self.request.query_params.get('assign_to')
        issue = Issues.objects.get(pk=pk)

        if AppUser.objects.get(pk=assign_to) in issue.project.members.all():
            serializer = IssueSerializer(issue, data={'assigned_to': assign_to}, partial=True)

            if serializer.is_valid():
                serializer.save()
                return Response({'status': 'Assignment Successful'}, status=status.HTTP_202_ACCEPTED)

        else:
            return Response({'Error': 'User not a Team Member'}, status=status.HTTP_406_NOT_ACCEPTABLE)

        #if AppUser.objects.get(pk=assign_to) in issue.project.members.all():

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return IssuePOSTSerializer
        else:
            return IssueGETSerializer
        
    @action(methods=['get',], detail=True, url_path='comments', url_name='comments')
    def get_issue_comments(self, request, pk):
        issue = Issues.objects.get(pk=pk)
        comments = Comment.objects.filter(issue=issue)
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    @action(methods=['get',], detail=False, url_path='add_issue', url_name='add_issue')
    def add_issue(self, request):
        if request.user.is_authenticated:
            title = request.GET.get('title')
            description = request.GET.get('description')
            bug_status = request.GET.get('bug_status')
            reported_by = request.user
            project_id = request.GET.get('project')
            project = Project.objects.get(pk = project_id)
            tag = request.GET.get('tag')
            print(title)
            print(description)
            print(bug_status)
            print(reported_by)
            print(project)
            print(tag)
            issue = Issues(title = title,description = description,bug_status = bug_status, reported_by = reported_by, project = project, tag = tag)
            issue.save()
            return Response({'Status':'This is working'})
        else: 
            return Response({'Status':'User not Authenticated'})

class CommentViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        try:
            return Comment.objects.filter(issue=self.kwargs['issue_pk'])
        except KeyError:
            return Comment.objects.all()
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer

    #permission_classes = [IsAdminOrReadOnly]
    @action(methods=['get',], detail=True, url_path='images', url_name='images')
    def get_comment_images(self, request, pk):
        comment = Comment.objects.get(pk=pk)
        images = Image.objects.filter(comment=comment)
        serializer = UploadImageSerializers(images, many=True)
        return Response(serializer.data)

class ImageViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        try:
            return Image.objects.filter(comment=self.kwargs['comment_pk'])
        except KeyError:
            return Image.objects.all()
    queryset = Image.objects.all()
    serializer_class = UploadImageSerializers

