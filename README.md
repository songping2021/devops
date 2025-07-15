# devops
一款基于gitlab开源的CICD可视化编辑器，本项目使用cursor编写
## 页面概览
![alt text](e0673f3efd172c2dbf859b66ebd7462.png)
![](dfb794a8658eeddc1cb3005973c818d.png)
![alt text](77ee8c4080ed84b107fef7b69b2238e.png)
![alt text](8861ee37f9a1823595b4f954165d9d7.png)
![alt text](6548ac5db009867c0d35f9218e1c5eb.png)
## 用法
修改backend\config\settings文件，更新数据库和gitlab实例地址为你本地的配置。
### 数据库连接配置
DB_CONFIG = {
    'dbname': '',
    'user': '',
    'password': '',
    'host': '',
    'port': ''
}

### GitLab API配置
GITLAB_API_URL = ''
GITLAB_NAMESPACE = 'cicd'  # GitLab命名空间/组
GITLAB_TOKEN = ''  # 替换为你的GitLab访问令牌