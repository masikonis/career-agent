from typing import List, Dict
from notion_client import Client
from .base import BaseKnowledge

class NotionKnowledge(BaseKnowledge):
    def __init__(self, api_key: str):
        self.client = Client(auth=api_key)
    
    def _get_rich_text_content(self, rich_text_list: List[Dict]) -> str:
        """Helper to extract text from rich_text array"""
        return ''.join([text['plain_text'] for text in rich_text_list])
    
    def _format_block_content(self, block: Dict) -> str:
        """Format different types of blocks into text"""
        block_type = block['type']
        
        if block_type == 'paragraph':
            text = self._get_rich_text_content(block['paragraph']['rich_text'])
            return text if text else ''
            
        elif block_type == 'heading_1':
            text = self._get_rich_text_content(block['heading_1']['rich_text'])
            return f"# {text}\n"
            
        elif block_type == 'heading_2':
            text = self._get_rich_text_content(block['heading_2']['rich_text'])
            return f"## {text}\n"
            
        elif block_type == 'heading_3':
            text = self._get_rich_text_content(block['heading_3']['rich_text'])
            return f"### {text}\n"
            
        elif block_type == 'bulleted_list_item':
            text = self._get_rich_text_content(block['bulleted_list_item']['rich_text'])
            return f"• {text}\n"
            
        elif block_type == 'numbered_list_item':
            text = self._get_rich_text_content(block['numbered_list_item']['rich_text'])
            return f"1. {text}\n"  # Note: all items will start with 1., but that's ok for plain text
            
        return ''  # Return empty string for unsupported block types
    
    async def get_page_content(self, page_id: str) -> Dict:
        """Fetch and format content from a Notion page"""
        try:
            all_blocks = []
            has_more = True
            next_cursor = None
            
            # Paginate through all blocks
            while has_more:
                response = self.client.blocks.children.list(
                    block_id=page_id,
                    start_cursor=next_cursor,
                    page_size=100
                )
                all_blocks.extend(response['results'])
                has_more = response['has_more']
                next_cursor = response['next_cursor'] if has_more else None
            
            # Process all blocks
            content_parts = []
            for block in all_blocks:
                text = self._format_block_content(block)
                if text:
                    content_parts.append(text)
            
            return {
                'content': '\n'.join(content_parts).strip()
            }
            
        except Exception as e:
            # Don't print error in test environment
            if 'invalid_id' not in str(e):
                print(f"Error fetching Notion page: {str(e)}")
            raise
    
    async def get_capabilities(self, database_id: str) -> List[Dict]:
        """Fetch capabilities from Notion database"""
        try:
            response = self.client.databases.query(database_id=database_id)
            
            # Transform the response to a simpler format
            capabilities = []
            for page in response['results']:
                props = page['properties']
                capability = {
                    'name': props['Name']['title'][0]['text']['content'],
                    'category': props['Category']['select']['name'],
                    'level': props['Level']['select']['name'],
                    'experience': props['Experience']['rich_text'][0]['text']['content'],
                    'examples': props['Examples']['rich_text'][0]['text']['content'] if props['Examples']['rich_text'] else ''
                }
                capabilities.append(capability)
            
            return capabilities
            
        except Exception as e:
            # Don't print error in test environment
            if 'invalid_id' not in str(e):
                print(f"Error fetching Notion database: {str(e)}")
            raise
