from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import render
from .models import KnowledgeComponent, KnowledgeNode,Glossary,Question, Student, Dependency,Glossary, Text, WordMapping
from .serializer import GlossarySerializer,QuestionSerializer, KnowledgeComponentSerializer, KnowledgeNodeSerializer, DependencySerializer, WordMappingSerializer, TextSerializer
from rest_framework import viewsets
from rest_framework import status, viewsets
from knowledge.models import KnowledgeComponent
from django.utils.timezone import now
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import F


# nodes views
class KnowledgeNodeViewSet(viewsets.ModelViewSet):
    queryset = KnowledgeNode.objects.all()
    serializer_class = KnowledgeNodeSerializer

#knowledge views
class KnowledgeComponentViewSet(viewsets.ModelViewSet):
    queryset = KnowledgeComponent.objects.all()
    serializer_class = KnowledgeComponentSerializer
    def update_dependencies_for_knowledge_component(self, main_kc, is_correct):
        """
        Update dependencies of a knowledge component for a student based on correctness.
        """
        dependencies = Dependency.objects.filter(main_node=main_kc.node)
        updated_dependencies = []

        for dependency in dependencies:
            # Fetch the dependent KnowledgeComponent for the same student
            dependent_kc = KnowledgeComponent.objects.filter(
                student=main_kc.student,
                node=dependency.dependent_node
            ).first()

            if dependent_kc:
                influence_prob = dependency.influence_probability
                old_p_know = dependent_kc.p_know

                # Apply positive or negative influence
                if is_correct and dependent_kc.p_know < dependent_kc.node.baseline:
                    dependent_kc.p_know += influence_prob * (1 - dependent_kc.p_know)
                elif not is_correct:
                    dependent_kc.p_know -= influence_prob * dependent_kc.p_know

                # Ensure `p_know` remains within bounds [0, 1]
                dependent_kc.p_know = max(0.0, min(dependent_kc.p_know, 1.0))
                dependent_kc.save()

                # Append updated dependency details to the response list
                updated_dependencies.append({
                    "dependent_node": dependent_kc.node.name,
                    "old_p_know": round(old_p_know, 4),
                    "updated_p_know": round(dependent_kc.p_know, 4),
                })
            else:
                updated_dependencies.append({
                    "dependent_node": dependency.dependent_node.name,
                    "error": f"Dependent KnowledgeComponent not found for student ID {main_kc.student.id}."
                })

        return updated_dependencies

    def calculate_probability(self, knowledge_component, node, is_correct):
        """
        Calculate and update the probability of a knowledge component.
        """
        if is_correct:
            p_correct = (
                knowledge_component.p_know * (1 - node.p_S) +
                (1 - knowledge_component.p_know) * node.p_G
            )
            posterior_mastery = (
                (knowledge_component.p_know * (1 - node.p_S)) / p_correct
            )
            if knowledge_component.p_know < node.baseline:
                knowledge_component.p_know = (
                    posterior_mastery + (1 - posterior_mastery) * node.p_T
                )
            else:
                knowledge_component.p_know = (
                    posterior_mastery + 0.1 * node.p_T
                )
        else:
            p_incorrect = (
                knowledge_component.p_know * node.p_S +
                (1 - knowledge_component.p_know) * (1 - node.p_G)
            )
            posterior_mastery = (
                (knowledge_component.p_know * node.p_S) / p_incorrect
            )
            knowledge_component.p_know = (
                posterior_mastery + (1 - posterior_mastery) * node.p_T
            )
        knowledge_component.p_know = max(0.0, min(knowledge_component.p_know, 1.0))
        return knowledge_component.p_know    
    @action(detail=False, methods=['post'])
    def update_probability(self, request):
        """
        Validate the user's answer and update the knowledge component.
        """
        try:
            # Extract required data from the request
            question_id = request.data.get("question_id")
            student_id = request.data.get("student_id")
            user_answer = request.data.get("answer")

            # Ensure required fields are provided
            if not all([question_id, student_id, user_answer]):
                return Response(
                    {"error": "Missing required fields (question_id, student_id, answer)."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Fetch the question
            question = get_object_or_404(Question, id=question_id)

            # Fetch the related KnowledgeNode dynamically by name
            node = KnowledgeNode.objects.filter(name=question.node).first()
            if not node:
                return Response(
                    {"error": f"KnowledgeNode with name '{question.node}' not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Validate the answer
            is_correct = question.answer.strip().lower() == user_answer.strip().lower()

            # Fetch the KnowledgeComponent for the node and student
            student = get_object_or_404(Student, id=student_id)
            knowledge_component = KnowledgeComponent.objects.filter(node=node, student=student).first()

            if not knowledge_component:
                return Response(
                    {"error": "KnowledgeComponent not found for the specified node and student."},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Update the main KnowledgeComponent probability
            knowledge_component.p_know = self.calculate_probability(knowledge_component, node, is_correct)
            knowledge_component.last_updated = timezone.now()
            knowledge_component.save()

            # Update dependencies of the main KnowledgeComponent
            updated_dependencies = self.update_dependencies_for_knowledge_component(knowledge_component, is_correct)

            # Return response
            return Response({
                "is_correct": is_correct,
                "main_knowledge_component": {
                    "node_name": node.name,
                    "student_name": student.user.username,
                    "p_know": knowledge_component.p_know,
                    "last_updated": knowledge_component.last_updated,
                },
                "updated_dependencies": updated_dependencies
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def search_gloss(self,word):
        try:
            # Find the KnowledgeNode associated with the word
            node = KnowledgeNode.objects.filter(name__icontains=word).first()
            if not node:
                return {
                    "error": f"The word '{word}' is not found in any KnowledgeNode."
                }

            # Check if a Glossary entry exists for the node
            glossary = Glossary.objects.filter(node=node).first()
            if glossary:
                return {
                    "gloss": glossary.gloss,
                    "definition": glossary.definition,                   
                    "Sentence":glossary.Sentence,
                    "node":glossary.node,                    
                }
            else:
                return {
                    "error": f"No glossary available for the word '{word}' associated with node '{node.name}'."
                }

        except Exception as e:
            return {"error": str(e)}
    #handle clicks:
    @action(detail=False, methods=['post'])
    def handle_click(self, request):
        """
        Handle a click event for a specific word.
        """
        try:
            # Parse input data
            text_id = request.data.get("text_id")
            surface_form = request.data.get("word")
            student_id = request.data.get("student_id")

            # Validate input data
            if not all([text_id, surface_form, student_id]):
                return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

            # Get the text and related grade/unit
            text = Text.objects.get(id=text_id)
            current_testing_grade = text.grade
            current_testing_unit = text.unit

            # Find the WordMapping and lemma
            word_mapping = WordMapping.objects.get(surface_form=surface_form)
            lemma = word_mapping.lemma
              
            # Find the corresponding KnowledgeComponent for the lemma and student
            knowledge_components = KnowledgeComponent.objects.select_related('node').filter(student_id=student_id)
            word_found = False

            for kc in knowledge_components:
                if lemma in kc.node.name: # Match lemma with node name
                    print("found")
                    word_found = True
                    # Increment click_count and save
                    kc.click_count = F('click_count') + 1
                    kc.last_updated = now()
                    kc.save()

                    # Reload the instance after update
                    kc.refresh_from_db()

                    # Determine testing status
                    is_tested_now = kc.node.grade == current_testing_grade and kc.node.unit == current_testing_unit
                    is_tested_later = kc.node.grade > current_testing_grade or (
                        kc.node.unit > current_testing_unit and kc.node.grade == current_testing_grade)
                    is_tested_past = kc.node.grade < current_testing_grade or (
                        kc.node.unit < current_testing_unit and kc.node.grade == current_testing_grade)
                    
                    # Apply rules based on click_count and testing status
                    if kc.click_count <= 2:
                        gloss_data = self.search_gloss(lemma)  # Call the glossary search function
                        if gloss_data:  # Ensure the glossary result is valid
                            return Response({
                                "action": "show_glossary",
                                "word": lemma,
                                "glossary": {
                                    "node": gloss_data.get("node"),
                                    "sentence": gloss_data.get("Sentence"),
                                    "gloss": gloss_data.get("gloss"),
                                    "definition": gloss_data.get("definition")
                                }
                            }, status=status.HTTP_200_OK)
                    if is_tested_later and kc.click_count > 3 :
                        kc.p_know = min(1.0, kc.p_know + 0.10)
                        kc.save()
                        return Response({"gloss": "show_glossary cause later", "word": lemma}, status=status.HTTP_200_OK)
                  
                    elif is_tested_past and kc.click_count == 1:
                        kc.p_know = max(0.0, kc.p_know - 0.05)
                        kc.save()
                        return Response({"gloss": "decay_applied", "word": lemma}, status=status.HTTP_200_OK)

                    elif kc.click_count > 3 and (is_tested_now or is_tested_past):
                        # Fetch a random question related to the node
                        kc.click_count = 0
                        kc.save()
                        question = Question.objects.filter(node=kc.node.name).order_by('?').first()
                        if question:
                            return Response({
                                "action": "ask_question",
                                "question_id": question.id,
                                "question_text": question.question
                            }, status=status.HTTP_200_OK)
            if not word_found:
                return Response({"gloss": "show_glossarycause not found ", "word": lemma}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class DependencyViewSet(viewsets.ModelViewSet):
    queryset = Dependency.objects.all()
    serializer_class = DependencySerializer
  
#question views 
class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    
#glossary views
class GlossaryViewSet(viewsets.ModelViewSet):
    queryset = Glossary.objects.all()
    serializer_class = GlossarySerializer

class WordMappingViewSet(viewsets.ModelViewSet):
    queryset = WordMapping.objects.all()
    serializer_class = WordMappingSerializer

class TextViewSet(viewsets.ModelViewSet):
    queryset = Text.objects.all()
    serializer_class = TextSerializer
    def get(self, request, unit,grade):
        texts = Text.objects.filter(unit=unit, grade= grade).values("id", "title", "grade", "unit")
        return Response(list(texts), status=status.HTTP_200_OK)
       
    @action(detail=False, methods=['get'], url_path='get-texts')
    def get_texts(self, request):
        # Retrieve query parameters from the request
        grade = request.query_params.get('grade')
        unit = request.query_params.get('unit')

        if not grade or not unit:
            return Response({"error": "Both 'grade' and 'unit' query parameters are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Filter texts based on grade and unit
        texts = Text.objects.filter(grade=grade, unit=unit).values("id", "title", "grade", "unit")

        return Response(list(texts), status=status.HTTP_200_OK)
    @action(detail=False, methods=['get'], url_path='get_text_by_id')
    def get_text_by_id(self, request):
        # Retrieve query parameters from the request
        id = request.query_params.get('id')
        if not id:
            return Response({"error": "Both 'grade' and 'unit' query parameters are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Filter texts based on grade and unit
        texts = Text.objects.filter(id=id).values("id", "title", "grade", "unit","content","image")

        return Response(list(texts), status=status.HTTP_200_OK)

