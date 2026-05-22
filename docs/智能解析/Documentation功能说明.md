***\*Documentation功能说明\****

![image-20260522102144668](C:\Users\1111\AppData\Roaming\Typora\typora-user-images\image-20260522102144668.png)

**概述**：该页面为某公司下全部文件的总览

**权限**：有该公司权限的管理端用户可以看到全部文件夹及文件夹下文件，公司端不可看到GS Internal文件夹



**页面说明**

**文件夹:**

Company, Product, KPA, Investment, Financial, GS Internal, Imported Statements

**Category**:

- Company: Product, Technology, Process, Security
- Product: Product, Technology, Process, Security
- KPA: Product, Technology, Process, Security
- Investment: GSV Document, GSH Document, Credit Memo Document, Warrant Document
- Financial: P&L ,  Balance Sheet , Proforma
- GS Internal: GS Internal
- Imported Statements: Benchmark Report

**文件来源**： 

- Company: Documentation页面上传，DI板块上传
- Product: Documentation页面上传，DI板块上传
- KPA:  KPA板块上传
- Investment: Investment页面上传
- Financial： FE页面上传
- GS Internal： Documentation页面上传
- Imported Statements: OCR功能上传

 **文件交互**：

- Company文件夹：四种Category,与DI板块相通，互相回显，两个板块的对应规则:
  - Company- Product  ↔ Product- Company
  - Company- Technology  ↔ Technology - Company
  - Company- Process ↔ Process- Company
  - Company- Security ↔ Security- Company
- Product文件夹：四种Category,与DI板块相通，互相回显，两个板块的对应规则:
  - Product- Company  ↔ Company- Product
  - Product- Technology  ↔ Technology - Product
  - Product- Process ↔ Process- Product
  - Product- Security ↔ Security- Product

- KPA文件夹：不支持在Documentation页面新增，仅回显KPA板块上传的文件
- Investment文件夹：不支持在Documentation页面新增，仅回显Investment板块上传的文件
- Financial文件夹：不支持在Documentation页面新增，仅回显Financial Entry板块上传的文件
- GS Internal文件夹：仅支持在Documentation页面新增
- Imported Statements文件夹：不支持在Documentation页面新增，仅回显OCR板块上传的文件

**操作:**

- 删除、下载、分享

**Filter：**

- Folder: Company, Product, KPA, Investment, Financial, GS Internal, Imported Statements
- Type:  Folder中所选的文件夹中包含的文档类型
- Category：上面两个筛选结果中包含的category

**列表字段：**

File name: 文件名

Uploaded by: 上传人name, 此处应为记录好的，而不是现拉取的ID对应的名字，以防用户被删除后此处无法正常显示

Size: 文件大小

Category: 文件对应的Category

**Add Documentation:**

该页面仅可添加上述描述中可在此页面上传的文件夹文件