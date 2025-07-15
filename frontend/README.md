# CI/CD流水线管理系统 - 前端项目

## 项目结构

```
frontend/
├── index.html                  # 主页面（流水线列表）
├── package.json               # 项目配置文件
├── README.md                  # 项目说明文档
├── pages/                     # 页面文件
│   └── pipeline-edit.html     # 流水线编辑页面
└── assets/                    # 静态资源
    ├── css/                   # 样式文件
    │   ├── styles.css         # 主样式文件
    │   └── pipeline-edit.css  # 流水线编辑页样式
    └── js/                    # JavaScript文件
        ├── config.js          # 配置文件
        ├── main.js           # 主入口文件
        ├── pipeline-api.js   # API接口模块
        ├── pipeline-edit-main.js  # 编辑页主文件
        ├── pipeline-loader.js     # 流水线加载器
        ├── task-manager.js        # 任务管理器
        ├── stage-manager.js       # 阶段管理器
        ├── state-manager.js       # 状态管理器
        ├── form-manager.js        # 表单管理器
        ├── utils.js              # 工具函数
        └── README.md             # JavaScript模块说明
```

## 功能特性

### 🚀 主要功能

1. **流水线管理**
   - 流水线列表查看
   - 创建新流水线
   - 编辑现有流水线
   - 删除流水线
   - 执行流水线

2. **任务配置**
   - 支持Maven项目配置
   - 支持NPM项目配置
   - 多阶段流程编排
   - 动态任务管理

3. **阶段配置**
   - 编译阶段配置
   - 构建阶段配置
   - 部署阶段配置
   - 侧边栏配置面板

4. **用户界面**
   - 响应式设计
   - 现代化UI组件
   - 友好的用户交互
   - 实时状态反馈

### 🛠️ 技术栈

- **HTML5** - 页面结构
- **CSS3** - 样式设计
- **JavaScript ES6+** - 业务逻辑
- **模块化架构** - 代码组织
- **RESTful API** - 后端通信

## 开发指南

### 环境要求

- Node.js >= 14.0.0（可选，用于开发服务器）
- 现代浏览器（支持ES6模块）

### 快速开始

1. **使用Node.js开发服务器（推荐）**
   ```bash
   cd frontend
   npm install
   npm start
   ```
   访问: http://localhost:3000

2. **使用Python简单服务器**
   ```bash
   cd frontend
   python -m http.server 3000
   ```
   访问: http://localhost:3000

3. **直接在浏览器中打开**
   ```bash
   # 直接双击 index.html 文件
   # 注意：某些功能可能因跨域限制无法正常工作
   ```

### 配置说明

**API接口配置** (`assets/js/config.js`):
```javascript
// API基础URL配置
window.API_BASE_URL = 'http://localhost:5000';

// 其他配置项...
```

### 目录说明

- **`pages/`** - 存放所有HTML页面文件
- **`assets/css/`** - 存放所有CSS样式文件
- **`assets/js/`** - 存放所有JavaScript文件
  - 模块化设计，每个功能模块独立
  - 使用ES6 import/export语法
  - 清晰的依赖关系

### 开发规范

1. **文件命名**
   - 使用小写字母和连字符
   - 有意义的文件名
   - 按功能模块组织

2. **代码规范**
   - 使用ES6+语法
   - 模块化开发
   - 清晰的注释
   - 统一的代码风格

3. **API调用**
   - 统一使用 `pipeline-api.js` 模块
   - 错误处理
   - 用户友好的提示信息

## 部署说明

### 静态文件部署

前端项目为纯静态文件，可部署到任何Web服务器：

1. **Nginx部署**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       root /path/to/frontend;
       index index.html;
       
       location / {
           try_files $uri $uri/ /index.html;
       }
   }
   ```

2. **Apache部署**
   ```apache
   <VirtualHost *:80>
       DocumentRoot "/path/to/frontend"
       ServerName your-domain.com
       
       <Directory "/path/to/frontend">
           AllowOverride All
           Require all granted
       </Directory>
   </VirtualHost>
   ```

### 配置调整

部署时需要修改API接口地址：

```javascript
// assets/js/config.js
window.API_BASE_URL = 'https://your-api-domain.com';
```

## 浏览器兼容性

- Chrome >= 60
- Firefox >= 60
- Safari >= 12
- Edge >= 79

## 故障排除

### 常见问题

1. **跨域错误**
   - 确保后端API启用了CORS
   - 使用开发服务器而不是直接打开HTML文件

2. **模块加载失败**
   - 检查文件路径是否正确
   - 确保使用支持ES6模块的浏览器

3. **API请求失败**
   - 检查后端服务是否正常运行
   - 确认API基础URL配置正确

### 调试建议

1. 打开浏览器开发者工具
2. 查看Console面板的错误信息
3. 检查Network面板的API请求状态
4. 使用断点调试JavaScript代码

## 维护和更新

### 添加新功能

1. 在相应的模块文件中添加功能
2. 更新API接口（如需要）
3. 添加相应的CSS样式
4. 更新文档

### 样式修改

- 主样式: `assets/css/styles.css`
- 页面特定样式: `assets/css/pipeline-edit.css`

### 功能扩展

- API模块: `assets/js/pipeline-api.js`
- 工具函数: `assets/js/utils.js`
- 页面逻辑: 对应的JavaScript文件

## 联系方式

- 项目团队: CICD Team
- 技术支持: 请参考项目文档或联系开发团队 