# Redirect Users to Benchmark Company Dashboard Upon New Financial Data - 需求文档

## 1. 功能概述

**功能目标**: 当用户提交新的财务数据时，系统自动引导用户查看最新的Benchmarking
**适用用户**: 使用财务管理功能的所有用户  
**核心价值**: 帮助用户快速获取最新财务数据对标的基准洞察，无需手动导航到Benchmarking页面，加速数据审查和决策流程

**关键特点**:
- 自动重定向机制（手动输入场景）
- 智能通知机制（非手动同步场景）
- 预设过滤器应用，无需用户额外配置
- 保持现有基准对标页面功能和数据完整性

---

## 2. 业务需求与完整流程

### **场景1：手动财务数据输入：手动填写或OCR上传（自动跳转）**

**流程步骤**：

1. **用户输入新closed month财务数据**


2. **自动跳转到基准对标页面**
   - 提交新closed month成功后，提交人将跳转到Company Benchmarking页面
   - 其他有该公司权限的人进入该公司Financial Entry页面，有条幅提示，条幅内容见场景2.3


3. **预设过滤器自动应用**
   - Benchmarking页面加载时，自动应用以下过滤器：
     - **报告期**：新提交closed month月份
     - **基准视图**：Actuals – Internal Peers（实际数据 – 内部同业）
   - 用户无需手动配置过滤条件，立即看到最相关的基准对比数据

---

### **场景2：非手动财务数据更新（通知提示）**

**流程步骤**：

1. **系统自动同步财务数据**
   - QuickBooks或其他第三方系统自动同步新的财务数据到LG
   - 系统识别closed month并可用

2. **生成通知消息**
   - 系统不会立即重定向用户
   - 而是在有该公司权限的用户下次登录时显示通知或toast消息，按照用户通知

3. **通知内容与行为**
   - **通知文案**：Benchmark Data Updated. Benchmark results for have been updated based on the latest financial data.
   - **通知形式**：Toast消息
   - **交互选项**：
     - 用户可点击通知中的链接，导航到Company Benchmarking页面 跳转完成后条幅关闭后续解除通知
     - 用户可点击"关闭"按钮，解除通知

4. **访问基准对标页面**
   - 用户点击通知链接时，跳转到Company Benchmarking页面
   - 页面加载时同样应用预设过滤器（新月份 + Actuals – Internal Peers视图）

---

