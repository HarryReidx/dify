#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quiz Flask Service 测试脚本

测试试卷生成服务的各种功能：
1. 单选题、多选题、判断题的混合处理
2. 题目正确分离
3. 选项完整性
4. 空白试卷生成（不预选答案）
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import post_process_quiz_html
import markdown
import re

def test_quiz_service():
    """测试试卷生成服务的完整功能"""
    
    # 测试用的Markdown内容
    test_content = """# 电石厂岗位定员与应急小组职责考核试卷

---

## 一、单选题  
1. 根据《电石厂应急预案》，应急小组组长在事故发生时的首要职责是什么？  
  - ( ) A. 立即对外发布新闻公告  
  - (x) B. 发布和解除分厂级应急救援命令、信号  
  - ( ) C. 直接参与现场伤员抢救  
  - ( ) D. 联系家属并安排疏散  

2. 应急小组组长在事故应急中，向公司汇报事故情况的职责属于哪一项？  
  - ( ) A. 组织修订应急预案  
  - ( ) B. 检查应急物资准备情况  
  - (x) C. 向公司汇报事故情况，必要时传达和实施应急行动  
  - ( ) D. 主持事故后的生产恢复会议  

3. 在电石厂应急预案编制过程中，谁应首先指定预案编制小组人员？  
  - ( ) A. 应急小组组长  
  - (x) B. 企业管理层  
  - ( ) C. 安全工程师  
  - ( ) D. 班组负责人  

---

## 二、多选题  
4. 以下哪些是应急小组组长的职责？（可多选）  
  - [x] A. 组织和指挥分厂级应急演练及事故应急救援工作  
  - [x] B. 组织指挥救援队伍实施救援行动，负责人员、资源配置、应急队伍的调动  
  - [x] C. 参与事故调查，总结应急救援经验教训  
  - [ ] D. 承担全部法律责任  
  - [x] E. 协调事故应急救援现场其它工作  

5. 应急救援预案的核心内容包括哪些？（可多选）  
  - [x] A. 明确应急组织和人员的职责  
  - [x] B. 对可能发生的事故进行预测和评价  
  - [x] C. 设计行动战术和程序  
  - [ ] D. 制定年度财务预算  
  - [x] E. 训练和演习  

---

## 三、判断题  
6. 应急演练结束后无需填写《应急演练评估表》。  
  - ( ) 正确  
  - (x) 错误  

7. 初始评估应描述事故发生后几分钟内观察到的现场情况，包括伤亡、损失及是否需要外界援助。  
  - (x) 正确  
  - ( ) 错误  """

    print("🧪 Quiz Flask Service 功能测试")
    print("=" * 60)
    
    try:
        # 使用markdown扩展转换
        extensions = [
            "tables", "app.extensions.checkbox", "app.extensions.radio",
            "app.extensions.textbox"
        ]
        
        print("📝 转换Markdown到HTML...")
        html = markdown.markdown(test_content,
                               extensions=extensions,
                               output_format="html5")
        
        print("🔧 后处理HTML结构...")
        processed_html = post_process_quiz_html(html)
        
        # 保存结果到文件
        output_file = 'quiz_test_result.html'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(processed_html)
        
        print(f"💾 结果已保存到: {output_file}")
        
        # 分析结果
        print(f"\n📊 试卷分析:")
        
        # 统计题目块
        question_blocks = re.findall(r'<div class="question-block[^"]*"[^>]*>', processed_html)
        radio_blocks = re.findall(r'<div class="question-block radio-question"[^>]*>', processed_html)
        checkbox_blocks = re.findall(r'<div class="question-block checklist-question"[^>]*>', processed_html)
        
        print(f"  总题目数: {len(question_blocks)} 个")
        print(f"  单选/判断题: {len(radio_blocks)} 个")
        print(f"  多选题: {len(checkbox_blocks)} 个")
        
        # 检查预选状态
        checked_radio = re.findall(r'<input[^>]*type="radio"[^>]*checked', processed_html)
        checked_checkbox = re.findall(r'<input[^>]*type="checkbox"[^>]*checked', processed_html)
        
        print(f"\n🔍 预选状态检查:")
        print(f"  预选的单选/判断题选项: {len(checked_radio)} 个")
        print(f"  预选的多选题选项: {len(checked_checkbox)} 个")
        
        # 验证每个题目的选项数量
        print(f"\n🔍 题目详细分析:")
        
        # 分析单选题和判断题
        radio_question_count = 0
        for block_match in re.finditer(r'<div class="question-block radio-question"[^>]*>.*?</div>', processed_html, re.DOTALL):
            radio_question_count += 1
            block_content = block_match.group(0)
            question_text_match = re.search(r'<div class="question-text">(.*?)</div>', block_content, re.DOTALL)
            question_text = question_text_match.group(1).strip() if question_text_match else "未知题目"
            
            options = re.findall(r'<li class="option-item">', block_content)
            question_type = "判断题" if "正确" in question_text or "错误" in question_text else "单选题"
            expected_options = 2 if question_type == "判断题" else 4
            
            status = "✅" if len(options) == expected_options else "❌"
            print(f"  {question_type} {radio_question_count}: {len(options)}/{expected_options} 个选项 {status}")
            if len(options) != expected_options:
                print(f"    题目: {question_text[:50]}...")
        
        # 分析多选题
        checkbox_question_count = 0
        for block_match in re.finditer(r'<div class="question-block checklist-question"[^>]*>.*?</div>', processed_html, re.DOTALL):
            checkbox_question_count += 1
            block_content = block_match.group(0)
            question_text_match = re.search(r'<div class="question-text">(.*?)</div>', block_content, re.DOTALL)
            question_text = question_text_match.group(1).strip() if question_text_match else "未知题目"
            
            options = re.findall(r'<li class="option-item">', block_content)
            expected_options = 5  # 多选题通常有5个选项
            
            status = "✅" if len(options) == expected_options else "❌"
            print(f"  多选题 {checkbox_question_count}: {len(options)}/{expected_options} 个选项 {status}")
            if len(options) != expected_options:
                print(f"    题目: {question_text[:50]}...")
        
        # 最终验证
        expected_total = 7  # 3单选 + 2多选 + 2判断
        expected_radio = 5   # 3单选 + 2判断
        expected_checkbox = 2  # 2多选
        
        print(f"\n✅ 最终验证:")
        total_correct = len(question_blocks) == expected_total
        radio_correct = len(radio_blocks) == expected_radio
        checkbox_correct = len(checkbox_blocks) == expected_checkbox
        blank_correct = len(checked_radio) == 0 and len(checked_checkbox) == 0
        
        print(f"  题目总数: {len(question_blocks)}/{expected_total} {'✅' if total_correct else '❌'}")
        print(f"  单选/判断题: {len(radio_blocks)}/{expected_radio} {'✅' if radio_correct else '❌'}")
        print(f"  多选题: {len(checkbox_blocks)}/{expected_checkbox} {'✅' if checkbox_correct else '❌'}")
        print(f"  空白试卷: {'✅' if blank_correct else '❌'} (无预选答案)")
        
        if total_correct and radio_correct and checkbox_correct and blank_correct:
            print(f"\n🎉 所有测试通过！Quiz Flask Service 工作正常！")
            print(f"📄 生成的试卷文件: {output_file}")
            return True
        else:
            print(f"\n❌ 部分测试未通过，请检查问题")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_quiz_service()
    if success:
        print(f"\n🚀 服务可以正常使用！")
        print(f"启动命令: python main.py")
        print(f"服务地址: http://127.0.0.1:5006")
    else:
        print(f"\n⚠️  服务存在问题，请检查修复")
    
    exit(0 if success else 1)