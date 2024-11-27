from rest_framework import serializers
from .models import KnowledgeNode, KnowledgeComponent, Glossary, Question,Dependency,Text

class KnowledgeNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeNode
        fields = '__all__'


class KnowledgeComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeComponent
        fields = '__all__'


class GlossarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Glossary
        fields = '__all__'


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'

        
class DependencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Dependency
        fields = '__all__'


        
class TextSerializer(serializers.ModelSerializer):
    class Meta:
        model = Text
        fields = '__all__'

class WordMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dependency
        fields = '__all__'

