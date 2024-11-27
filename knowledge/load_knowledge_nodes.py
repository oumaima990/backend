import json
from django.core.management.base import BaseCommand
from models import KnowledgeNode  # Replace 'app_name' with your app's name

class Command(BaseCommand):
    help = 'Load knowledge nodes from JSON file'

    def handle(self, *args, **kwargs):
        file_path = r'C:\Users\Oumaima Elmarzouky\capstonebackend\capstonebackend\Data\knowledge_nodes.json'
        with open(file_path, 'r') as f:
            data = json.load(f)

        for item in data:
            KnowledgeNode.objects.create(
                name=item.get('name'),
                description=item.get('description')
                # Map other fields here
            )

        self.stdout.write(self.style.SUCCESS('Data inserted successfully!'))
