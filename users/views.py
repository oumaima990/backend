from django.shortcuts import render
from rest_framework import viewsets
from .models import Teacher, Student,CustomUser
from knowledge.models import KnowledgeComponent, KnowledgeNode
from .serializer import TeacherSerializer, StudentSerializer
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import render
from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.contrib.auth import login as django_login, logout as django_logout
from django.db import IntegrityError
from django.contrib.auth import login as django_login, authenticate

#teacher views 
class TeacherViewSet(viewsets.ModelViewSet):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer
    #gets informatio for all students 
    @action(detail=False, methods=['get'])
    def getstudentdetail(self, request, student_id):
        student = get_object_or_404(Student, id=student_id)
        components = KnowledgeComponent.objects.filter(student=student).select_related('node')
        progress = [
            {
                "unit": kc.node.unit,
                "grade": kc.node.grade,
                "mastery_percentage": round(kc.p_know * 100, 2),
            }
            for kc in components
        ]
        return Response({"id": student.id, "name": student.name, "email": student.email, "progress": progress}, status=status.HTTP_200_OK)
    #get students all
    def get_all_studnets(self, request):
        students = Student.objects.all().values("id", "name", "email")
        student_list = []
        for student in students:
            components = KnowledgeComponent.objects.filter(student_id=student["id"])
            mastery_percentage = (
                sum([kc.p_know for kc in components]) / len(components) * 100
                if components.exists()
                else 0.0
            )
            student["mastery_percentage"] = round(mastery_percentage, 2)
            student_list.append(student)
        return Response(student_list, status=status.HTTP_200_OK)
    def create(self, request, *args, **kwargs):
        # Extract data from the request
        data = request.data
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        # Check if required fields are provided
        if not all([username, email, password]):
            return Response(
                {"error": "Username, email, and password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Create the CustomUser instance
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_teacher=True  # Set the `is_teacher` flag
            )

            # Create the Teacher instance and link it to the CustomUser
            teacher = Teacher.objects.create(user=user)

            # Return the serialized Teacher data
            return Response(
                {
                    "id": teacher.id,
                    "username": user.username,
                    "email": user.email
                },
                status=status.HTTP_201_CREATED
            )
        except IntegrityError:
            return Response(
                {"error": "A user with this username or email already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )
#student views
class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    #the creation of a student = created of the node sets:
    @action(detail=False, methods=["get"], url_path="details/(?P<username>[^/.]+)")
    def details(self, request, username=None):
        """
        Fetch user details by username.
        """
        # Get the user associated with the given username
        user = get_object_or_404(CustomUser, username=username)

        # Serialize the user data
        user_data = {
            "username": user.username,
            "email": user.email,
            "is_student": user.is_student,
            "is_teacher": user.is_teacher,
            "id":user.id
        }

        return Response(user_data)

    def create(self, request, *args, **kwargs):
        # Extract required data from the request
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")
        teacher_id = request.data.get("teacher_id")

        if not all([username, email, password, teacher_id]):
            return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate the teacher exists
        teacher = get_object_or_404(Teacher, id=teacher_id)

        try:
            # Create the CustomUser
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_student=True
            )

            # Create the Student and link it to the teacher and user
            student = Student.objects.create(user=user, teacher=teacher)

            # Automatically create KnowledgeComponents for all KnowledgeNodes
            knowledge_nodes = KnowledgeNode.objects.all()
            for node in knowledge_nodes:
                KnowledgeComponent.objects.create(
                    node=node,
                    student=student,
                    p_know=node.p_L0  # Initialize with the node's p_L0
                )

            # Return success response
            return Response({
                "success": True,
                "student_id": student.id,
                "username": user.username,
                "email": user.email,
                "teacher": teacher.user.username  # Reference teacher's associated user
            }, status=status.HTTP_201_CREATED)

        except IntegrityError as e:
            # Handle username or email uniqueness error
            return Response({
                "success": False,
                "error": "Username or email already exists."
            }, status=status.HTTP_400_BAD_REQUEST)
    # Get all student details
    @action(detail=False, methods=['get'])
    def get_all_students_teacher_based(self, request):
        teacher_id = request.query_params.get('teacher_id')  # Retrieve teacher_id from query parameters

        if not teacher_id:
            return Response({"error": "Missing teacher_id parameter."}, status=status.HTTP_400_BAD_REQUEST)

        # Filter students based on teacher_id
        students = Student.objects.filter(teacher__id=teacher_id).select_related('user', 'teacher')

        student_list = [
            {
                "id": student.id,
                "username": student.user.username,
                "email": student.user.email,
                "teacher": student.teacher.user.username if student.teacher else None,
            }
            for student in students
        ]

        return Response(student_list, status=status.HTTP_200_OK)
    @action(detail=False, methods=['get'])
    def get_student_knowledge_components(self, request):
        student_id = request.query_params.get("student_id")
        if not student_id:
            return Response({"error": "Missing student_id parameter."}, status=status.HTTP_400_BAD_REQUEST)

        # Get the student instance
        student = get_object_or_404(Student, id=student_id)

        # Get the student's knowledge components
        knowledge_components = KnowledgeComponent.objects.filter(student=student).select_related('node')

        # Build the response data
        components_data = [
            {
                "component_name": kc.node.name,  # Assuming `name` field exists in `node`
                "mastery_percentage": round(kc.p_know * 100, 2),  # Convert to percentage
            }
            for kc in knowledge_components
        ]

        return Response(
            {
                "student_id": student.id,
                "student_username": student.user.username,
                "password": student.user.password,
                "knowledge_components": components_data,
            },
            status=status.HTTP_200_OK
        )
  

    @action(detail=False, methods=['post'])
    def login(self, request):
        import logging

        logger = logging.getLogger(__name__)
        username = request.data.get("username")
        password = request.data.get("password")

        if not all([username, password]):
            return Response({"error": "Missing username or password."}, status=status.HTTP_400_BAD_REQUEST)

        # Authenticate the user
        logger.debug(f"Authenticating user: Username={username}, Password={password}")
        user = authenticate(request, username=username, password=password)

        if user:
            # Log the user in and set session
            django_login(request, user)
            logger.info("Authentication successful.")

            if hasattr(user, 'is_student') and user.is_student:
                student = Student.objects.filter(user=user).first()
                if student:
                    request.session['student_id'] = student.id
                    return Response(
                        {
                            "success": True,
                            "user_type": "student",
                            "student_name": user.username,
                            "redirect_url": "/units/",
                            "id": user.id
                        },
                        status=status.HTTP_200_OK
                    )
            elif hasattr(user, 'is_teacher') and user.is_teacher:
                teacher = Teacher.objects.filter(user=user).first()
                if teacher:
                    request.session['teacher_id'] = teacher.id
                    return Response(
                        {
                            "success": True,
                            "user_type": "teacher",
                            "teacher_name": user.username,
                            "redirect_url": "/teacher-dashboard/",
                            "id": user.id

                        },
                        status=status.HTTP_200_OK
                    )
        else:
            logger.error("Authentication failed.")
            # Invalid credentials or user not found
            return Response(
                {"success": False, "error": "Invalid username or password."},
                status=status.HTTP_400_BAD_REQUEST
            )
    @action(detail=False, methods=['post'])
    def logout(self, request):
        django_logout(request)
        request.session.flush()
        return Response({"success": True, "message": "Logged out successfully."}, status=status.HTTP_200_OK)