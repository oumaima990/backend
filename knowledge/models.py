from django.db import models
from users.models import Student, Teacher
from django.utils import timezone  # Import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, viewsets

#knowledge nodes that remain the same 
class KnowledgeNode(models.Model):
    name = models.CharField(max_length=255, unique=True)  # E.g., "KC_Vocab_بعيد"
    description = models.TextField(blank=True, null=True)
    p_L0 = models.FloatField()  # Initial knowledge probability
    p_T = models.FloatField()   # Transition probability
    p_G = models.FloatField()   # Guessing probability
    p_S = models.FloatField()   # Slipping probability
    baseline = models.FloatField()  # Baseline threshold
    grade = models.IntegerField() #the grade the node belongs to
    unit= models.IntegerField() #the usit the node belongs to 
    def __str__(self):
        return self.name
    
#model links 
class KnowledgeComponent(models.Model):
    node = models.ForeignKey(KnowledgeNode, on_delete=models.CASCADE, related_name="components")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="knowledge_components")
    p_know = models.FloatField(default=0.0)  # Current knowledge probability, initialized to node's p_L0
    click_count = models.IntegerField(default=0)
    last_updated = models.DateTimeField(null=True, blank=True)  # Allow null values initially

    def save(self, *args, **kwargs):
        # Initialize p_know with the node's initial probability (p_L0) when first created
        if self._state.adding and not self.p_know:
            self.p_know = self.node.p_L0
        super().save(*args, **kwargs)
         # Manually update `last_updated` only when needed (not on creation)
        if not self._state.adding:
            self.last_updated = timezone.now()
    def __str__(self):
        return f"{self.node.name} (Student: {self.student.name})"
   

#glossary
class Glossary(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit auto-incrementing ID
    node = models.CharField(max_length=255, unique=True) 
    Sentence = models.CharField(max_length=25)
    gloss = models.TextField(null=True)
    definition = models.TextField()
    def __str__(self):
        return f"Glossary for {self.node.name}"

#questions
class Question(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit auto-incrementing ID
    QUESTION_TYPES = (
        ("multiple_choice", "Multiple Choice"),
        ("fill_in_blank", "Fill in the Blank"),
    )
    node = models.CharField(max_length=255) 
    type = models.CharField(max_length=50, choices=QUESTION_TYPES)
    question = models.TextField()
    options = models.JSONField(blank=True, null=True)  # Only for multiple-choice
    answer = models.TextField()

    def __str__(self):
        return f"Question for {self.node.name}: {self.question[:50]}"

#dependencies 
from django.db import models

class Dependency(models.Model):
    # Main node that influences other nodes
    main_node = models.ForeignKey(
        "KnowledgeNode", 
        on_delete=models.CASCADE, 
        related_name="dependencies"
    )
    # Dependent node that is influenced by the main node
    dependent_node = models.ForeignKey(
        "KnowledgeNode", 
        on_delete=models.CASCADE, 
        related_name="influences"
    )
    # Influence probability between nodes
    influence_probability = models.FloatField()

    def __str__(self):
        return f"{self.main_node.name} -> {self.dependent_node.name} ({self.influence_probability})"


class Text(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit auto-incrementing ID
    content = models.TextField()  # Original text
    title = models.CharField(max_length=255, null=True, blank=True)  # Optional: Title of the text
    grade = models.IntegerField() #the grade the node belongs to
    unit= models.IntegerField() #the usit the node belongs to 
    image = models.ImageField(upload_to='text_images/', null=True, blank=True)  # Store in 'media/text_images/'

class WordMapping(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit ID for WordMapping
    text = models.ForeignKey(Text, on_delete=models.CASCADE, related_name="word_mappings")  # Link to Text by its ID
    surface_form = models.CharField(max_length=255)  # Inflected word as it appears in the text
    lemma = models.CharField(max_length=255)  # Corresponding lemma
    knowledge_component = models.ForeignKey("KnowledgeComponent", on_delete=models.CASCADE, null=True, blank=True)  # Link to KC if exists