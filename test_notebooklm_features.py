"""
Test Script for NotebookLM Features
Test document summarization and question generation
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.ai_generator import generate_document_summary, generate_suggested_questions
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test document content
test_content = """
Web Penetration Testing Roadmap

Phase 1: Foundation Building
- Master Python scripting for security automation
- Deep dive into Linux command line and bash scripting
- Understand networking protocols (TCP/IP, HTTP/HTTPS, DNS)

Phase 2: Core Web Security
- Learn OWASP Top 10 vulnerabilities
- Master Cross-Site Scripting (XSS) attacks and defenses
- Understanding SQL Injection techniques
- Practice with Burp Suite and OWASP ZAP

Phase 3: Advanced Topics
- API Security Testing (REST, GraphQL)
- JWT token manipulation
- Session management vulnerabilities
- Authentication bypass techniques

Phase 4: Real-World Practice
- CTF challenges and bug bounty platforms
- HackTheBox and TryHackMe labs
- Responsible disclosure practices
"""

def test_summary_generation():
    """Test document summary generation"""
    print("=" * 60)
    print("TEST 1: Document Summary Generation")
    print("=" * 60)
    
    summary, key_points = generate_document_summary(
        test_content, 
        "Web-Penetration-Testing-Roadmap.pdf"
    )
    
    print("\n📄 SUMMARY:")
    print(summary)
    
    print("\n🔑 KEY POINTS:")
    for i, point in enumerate(key_points, 1):
        print(f"  {i}. {point}")
    
    print("\n✅ Summary generation test completed!")
    return summary, key_points

def test_question_generation():
    """Test suggested questions generation"""
    print("\n" + "=" * 60)
    print("TEST 2: Suggested Questions Generation")
    print("=" * 60)
    
    questions = generate_suggested_questions(
        test_content,
        "Web-Penetration-Testing-Roadmap.pdf"
    )
    
    print("\n💭 SUGGESTED QUESTIONS:")
    for i, q in enumerate(questions, 1):
        print(f"  {i}. {q}")
    
    print("\n✅ Question generation test completed!")
    return questions

def main():
    """Run all tests"""
    print("\n🧪 TESTING NOTEBOOKLM FEATURES - PHASE 1\n")
    
    # Check API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY not found in .env")
        print("Please set your API key first!")
        return
    
    print(f"✅ API Key found: {api_key[:10]}...{api_key[-5:]}\n")
    
    # Run tests
    try:
        summary, key_points = test_summary_generation()
        questions = test_question_generation()
        
        # Success summary
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        print(f"\n✅ Generated summary: {len(summary)} characters")
        print(f"✅ Generated key points: {len(key_points)} points")
        print(f"✅ Generated questions: {len(questions)} questions")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
