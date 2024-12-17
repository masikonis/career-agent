import pytest
import pytest_asyncio
from typing import List, Dict
from src.profile.manager import ProfileManager
from src.profile.base import ProfileDataSource

class MockProfileDataSource(ProfileDataSource):
    async def get_capabilities(self) -> List[Dict]:
        return [
            # Hard Skills
            {
                'name': 'Python',
                'category': 'Hard Skills',
                'level': 'Expert',
                'experience': 'Advanced Python development including async programming and ML',
                'examples': 'Built ML pipelines, async web services, and data processing systems'
            },
            {
                'name': 'Machine Learning',
                'category': 'Hard Skills',
                'level': 'Intermediate',
                'experience': 'Experience with ML frameworks and model deployment',
                'examples': 'Implemented classification and regression models using scikit-learn'
            },
            {
                'name': 'Data Structures',
                'category': 'Hard Skills',
                'level': 'Advanced',
                'experience': 'Deep understanding of algorithms and data structures',
                'examples': 'Optimized system performance using appropriate data structures'
            },
            # Soft Skills
            {
                'name': 'Team Leadership',
                'category': 'Soft Skills',
                'level': 'Advanced',
                'experience': 'Led multiple development teams across different projects',
                'examples': 'Successfully managed 5-person team for enterprise project delivery'
            },
            {
                'name': 'Communication',
                'category': 'Soft Skills',
                'level': 'Expert',
                'experience': 'Excellent verbal and written communication skills',
                'examples': 'Regular presentations to stakeholders and technical documentation'
            },
            # Tools/Platforms
            {
                'name': 'AWS',
                'category': 'Tools/Platforms',
                'level': 'Advanced',
                'experience': 'Extensive experience with AWS cloud services',
                'examples': 'Deployed and managed EC2, Lambda, S3, and RDS services'
            },
            {
                'name': 'Docker',
                'category': 'Tools/Platforms',
                'level': 'Intermediate',
                'experience': 'Container orchestration and deployment',
                'examples': 'Created and managed multi-container applications'
            },
            {
                'name': 'Git',
                'category': 'Tools/Platforms',
                'level': 'Basic',
                'experience': 'Version control and collaboration',
                'examples': 'Basic repository management and branching'
            },
            # Domain Knowledge
            {
                'name': 'Fintech',
                'category': 'Domain Knowledge',
                'level': 'Intermediate',
                'experience': 'Understanding of financial technology systems',
                'examples': 'Worked on payment processing and banking integration projects'
            },
            {
                'name': 'Agile Methodologies',
                'category': 'Domain Knowledge',
                'level': 'Advanced',
                'experience': 'Scrum and Kanban implementation experience',
                'examples': 'Led agile transformations and sprint planning'
            }
        ]

@pytest_asyncio.fixture
async def profile_manager():
    manager = ProfileManager(MockProfileDataSource())
    return manager

@pytest.mark.asyncio
async def test_get_capabilities(profile_manager):
    capabilities = await profile_manager.get_capabilities()
    assert len(capabilities) == 10
    assert capabilities[0]['name'] == 'Python'

@pytest.mark.asyncio
async def test_get_capabilities_by_category(profile_manager):
    hard_skills = await profile_manager.get_capabilities_by_category('Hard Skills')
    assert len(hard_skills) == 3
    assert all(skill['category'] == 'Hard Skills' for skill in hard_skills)

@pytest.mark.asyncio
async def test_search_capabilities(profile_manager):
    results = await profile_manager.search_capabilities('python machine learning')
    assert len(results) > 0
    assert any(cap['name'] == 'Python' for cap in results)
    assert any(cap['name'] == 'Machine Learning' for cap in results)

@pytest.mark.asyncio
async def test_match_requirements(profile_manager):
    requirements = ['Python', 'AWS', 'Team Management']
    matches = await profile_manager.match_requirements(requirements)
    
    assert isinstance(matches['match_score'], float)
    assert len(matches['matched_skills']) > 0
    assert 'Python' not in matches['missing_skills']

@pytest.mark.asyncio
async def test_expertise_distribution(profile_manager):
    distribution = await profile_manager.get_expertise_distribution()
    
    assert len(distribution['Expert']) == 2
    assert len(distribution['Advanced']) == 4
    assert len(distribution['Intermediate']) == 3
    assert len(distribution['Basic']) == 1

@pytest.mark.asyncio
async def test_find_related_capabilities(profile_manager):
    related = await profile_manager.find_related_capabilities('Python')
    assert len(related) > 0
    # Machine Learning should be related to Python due to similar context
    assert any(cap['name'] == 'Machine Learning' for cap in related)

@pytest.mark.asyncio
async def test_generate_skill_summary(profile_manager):
    # Test brief summary
    brief = await profile_manager.generate_skill_summary('brief')
    assert 'top_expertise' in brief
    assert 'expertise_levels' in brief
    
    # Test technical summary
    technical = await profile_manager.generate_skill_summary('technical')
    assert 'technical_expertise' in technical
    assert 'core_technologies' in technical
    
    # Test business summary
    business = await profile_manager.generate_skill_summary('business')
    assert 'key_strengths' in business
    assert 'domain_expertise' in business

@pytest.mark.asyncio
async def test_invalid_summary_format(profile_manager):
    with pytest.raises(ValueError):
        await profile_manager.generate_skill_summary('invalid_format') 

@pytest.mark.asyncio
async def test_get_capabilities_by_level(profile_manager):
    expert_skills = await profile_manager.get_capabilities_by_level('Expert')
    assert len(expert_skills) == 2
    assert 'Python' in [skill['name'] for skill in expert_skills]
    
    advanced_skills = await profile_manager.get_capabilities_by_level('Advanced')
    assert len(advanced_skills) == 4
    
    # Test case insensitivity
    expert_skills_lower = await profile_manager.get_capabilities_by_level('expert')
    assert len(expert_skills_lower) == 2

@pytest.mark.asyncio
async def test_get_top_capabilities(profile_manager):
    # Test with specific limit
    top_skills = await profile_manager.get_top_capabilities(limit=2)
    assert len(top_skills) == 2
    assert top_skills[0]['level'] in ['Expert', 'Advanced']
    
    # Test with limit larger than available skills
    all_top = await profile_manager.get_top_capabilities(limit=5)
    assert len(all_top) == 5
    assert all(skill['level'] in ['Expert', 'Advanced'] for skill in all_top)
    
    # Test with invalid limit
    invalid_limit = await profile_manager.get_top_capabilities(limit='invalid')
    assert len(invalid_limit) == 5
    assert all(skill['level'] in ['Expert', 'Advanced'] for skill in invalid_limit)

@pytest.mark.asyncio
async def test_edge_cases(profile_manager):
    # Empty search
    empty_search = await profile_manager.search_capabilities('')
    assert len(empty_search) == 0
    
    # Non-existent category
    non_existent = await profile_manager.get_capabilities_by_category('NonExistent')
    assert len(non_existent) == 0
    
    # Empty requirements
    empty_req_match = await profile_manager.match_requirements([])
    assert empty_req_match['match_score'] == 0
    
    # Non-existent capability for related search
    non_existent_related = await profile_manager.find_related_capabilities('NonExistent')
    assert len(non_existent_related) == 0
