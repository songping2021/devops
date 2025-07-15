#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import base64
from pathlib import Path
from backend.config.settings import GITLAB_API_URL, GITLAB_NAMESPACE, GITLAB_TOKEN

class GitLabClient:
    """GitLab API客户端"""
    
    def __init__(self):
        self.api_url = GITLAB_API_URL
        self.namespace = GITLAB_NAMESPACE
        self.token = GITLAB_TOKEN
        self.headers = {
            "PRIVATE-TOKEN": self.token,
            "Content-Type": "application/json"
        }
        # 获取cicd组的ID
        self.namespace_id = self._get_namespace_id()
    
    def _get_namespace_id(self):
        """获取cicd组的namespace_id"""
        try:
            url = f"{self.api_url}/groups/{self.namespace}"
            response = requests.get(url, headers=self.headers, verify=False)
            if response.status_code == 200:
                group = response.json()
                return group.get('id')
            else:
                print(f"无法获取组'{self.namespace}'的ID: {response.text}")
                return None
        except Exception as e:
            print(f"获取组ID异常: {e}")
            return None
    
    def create_project(self, project_id):
        """
        在GitLab上创建项目，如果项目已存在则直接返回项目信息
        项目将创建在cicd组下，使用用户输入的项目ID作为项目名
        
        Args:
            project_id: 项目ID (用户输入)
            
        Returns:
            dict: 项目信息
        """
        # 首先尝试获取项目信息，检查项目是否已存在
        try:
            existing_project = self.get_project(project_id)
            print(f"项目 cicd/{project_id} 已存在，直接使用现有项目")
            return existing_project
        except Exception as e:
            # 项目不存在，创建新项目
            print(f"项目 cicd/{project_id} 不存在，创建新项目: {str(e)}")
            
            url = f"{self.api_url}/projects"
            
            # 检查是否获取到了正确的namespace_id
            if not self.namespace_id:
                raise Exception(f"无法获取组'{self.namespace}'的ID，请检查组是否存在或权限是否足够")
            
            data = {
                "name": str(project_id),  # 项目显示名称使用原始project_id
                "path": str(project_id),  # 项目路径使用原始project_id
                "namespace_id": self.namespace_id,  # 使用cicd组的ID
                "visibility": "internal",
                "initialize_with_readme": False,
                "description": f"CICD项目 {project_id}"
            }
            
            print(f"创建项目请求数据: {data}")
            
            # 在调用API时忽略SSL验证
            response = requests.post(url, json=data, headers=self.headers, verify=False)
            
            if response.status_code == 201:
                project_info = response.json()
                print(f"成功创建GitLab项目: cicd/{project_id}")
                return project_info
            else:
                # 详细记录错误信息
                error_msg = f"创建GitLab项目失败: {response.text}"
                print(f"GitLab同步失败: {error_msg}")
                
                # 如果是因为项目名冲突或保留名称，提供更友好的错误信息
                if "reserved name" in response.text.lower():
                    error_msg = f"项目ID '{project_id}' 是GitLab保留名称，请使用其他项目ID"
                elif "has already been taken" in response.text.lower():
                    error_msg = f"项目名 '{project_id}' 已被占用，请使用其他项目ID"
                
                raise Exception(error_msg)
    
    def get_project(self, project_id):
        """
        获取GitLab项目信息
        
        Args:
            project_id: 项目ID
            
        Returns:
            dict: 项目信息
        """
        # 构建项目路径: cicd/project_id
        project_path = f"{self.namespace}%2F{project_id}"
        url = f"{self.api_url}/projects/{project_path}"
        
        response = requests.get(url, headers=self.headers, verify=False)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"获取GitLab项目失败: {response.text}")
    
    def upload_file(self, project_id, file_path, content, branch="main", commit_message="添加文件"):
        """
        上传文件到GitLab项目
        
        Args:
            project_id: 项目ID
            file_path: 文件路径
            content: 文件内容
            branch: 分支名
            commit_message: 提交信息
            
        Returns:
            dict: 上传结果
        """
        # 构建项目路径: cicd/project_id
        project_path = f"{self.namespace}%2F{project_id}"
        url = f"{self.api_url}/projects/{project_path}/repository/files/{requests.utils.quote(file_path, safe='')}"
        
        data = {
            "branch": branch,
            "content": content,
            "commit_message": commit_message
        }
        
        try:
            # 检查文件是否已存在
            check_response = requests.get(url, headers=self.headers, params={"ref": branch}, verify=False)
            
            if check_response.status_code == 200:
                # 文件已存在，更新文件
                response = requests.put(url, json=data, headers=self.headers, verify=False)
            else:
                # 文件不存在，创建文件
                response = requests.post(url, json=data, headers=self.headers, verify=False)
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                raise Exception(f"上传文件到GitLab失败: {response.text}")
                
        except Exception as e:
            raise Exception(f"上传文件到GitLab项目 cicd/{project_id} 失败: {str(e)}")
    
    def upload_directory(self, project_id, local_path, gitlab_path, branch="main"):
        """
        上传目录到GitLab项目
        
        Args:
            project_id: 项目ID
            local_path: 本地路径
            gitlab_path: GitLab路径
            branch: 分支名
        """
        local_dir = Path(local_path)
        
        # 如果本地目录不存在，创建一个空目录
        if not local_dir.exists():
            local_dir.mkdir(parents=True, exist_ok=True)
        
        # 首先确保项目存在
        try:
            project_info = self.get_project(project_id)
            print(f"找到GitLab项目: {project_info.get('name', project_id)}")
        except Exception as e:
            print(f"项目不存在，尝试创建: {e}")
            try:
                project_info = self.create_project(project_id)
                print(f"成功创建GitLab项目: {project_info.get('name', project_id)}")
            except Exception as create_error:
                print(f"创建项目失败: {create_error}")
                # 即使创建失败，也不中断文件上传，只是记录错误
        
        # 递归遍历目录中的所有文件
        upload_success_count = 0
        upload_error_count = 0
        
        for file_path in local_dir.glob('**/*'):
            if file_path.is_file():
                try:
                    # 构建GitLab中的相对路径
                    relative_path = file_path.relative_to(local_dir)
                    gitlab_file_path = f"{gitlab_path}/{relative_path}".replace('\\', '/')
                    
                    # 读取文件内容
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            content = file.read()
                    except UnicodeDecodeError:
                        # 如果UTF-8解码失败，尝试以二进制方式读取并进行base64编码
                        with open(file_path, 'rb') as file:
                            binary_content = file.read()
                            content = base64.b64encode(binary_content).decode('ascii')
                            print(f"文件 {file_path} 以二进制方式读取并进行base64编码")
                    
                    # 上传文件到GitLab
                    self.upload_file(
                        project_id=project_id,
                        file_path=gitlab_file_path,
                        content=content,
                        branch=branch,
                        commit_message=f"添加文件: {gitlab_file_path}"
                    )
                    upload_success_count += 1
                    print(f"成功上传文件: {gitlab_file_path}")
                    
                except Exception as e:
                    upload_error_count += 1
                    print(f"上传文件 {file_path} 失败: {str(e)}")
                    # 继续处理其他文件，不中断整个上传过程
        
        print(f"目录上传完成: 成功{upload_success_count}个文件，失败{upload_error_count}个文件")
    
    def delete_project(self, project_id):
        """
        删除GitLab项目
        
        Args:
            project_id: 项目ID
            
        Returns:
            bool: 删除是否成功
        """
        project_path = f"{self.namespace}%2F{project_id}"
        url = f"{self.api_url}/projects/{project_path}"
        
        response = requests.delete(url, headers=self.headers, verify=False)
        
        if response.status_code in [202, 204]:
            print(f"成功删除GitLab项目: cicd/{project_id}")
            return True
        else:
            raise Exception(f"删除GitLab项目 cicd/{project_id} 失败: {response.text}")
    
    def delete_file(self, project_id, file_path, branch="main"):
        """
        删除GitLab项目中的文件
        
        Args:
            project_id: 项目ID
            file_path: 文件路径
            branch: 分支名
            
        Returns:
            bool: 删除是否成功
        """
        project_path = f"{self.namespace}%2F{project_id}"
        url = f"{self.api_url}/projects/{project_path}/repository/files/{requests.utils.quote(file_path, safe='')}"
        data = {
            "branch": branch,
            "commit_message": f"删除文件: {file_path}"
        }
        
        response = requests.delete(url, headers=self.headers, params=data, verify=False)
        
        if response.status_code not in [200, 204]:
            print(f"删除GitLab文件失败: cicd/{project_id}/{file_path}, 状态码: {response.status_code}, 响应: {response.text}")
        else:
            print(f"成功删除GitLab文件: cicd/{project_id}/{file_path}")
    
    def delete_directory(self, project_id, directory_path):
        """
        删除GitLab项目中的目录（递归删除所有文件）
        
        Args:
            project_id: 项目ID
            directory_path: 目录路径
            
        Returns:
            bool: 删除是否成功
        """
        try:
            project_path = f"{self.namespace}%2F{project_id}"
            # 获取目录下的所有文件
            url = f"{self.api_url}/projects/{project_path}/repository/tree"
            params = {"path": directory_path, "recursive": True}
            
            response = requests.get(url, headers=self.headers, params=params, verify=False)
            
            if response.status_code == 200:
                files = response.json()
                deleted_count = 0
                
                # 删除目录下的所有文件
                for file_info in files:
                    if file_info["type"] == "blob":  # 只删除文件，不删除子目录
                        try:
                            self.delete_file(project_id, file_info["path"])
                            deleted_count += 1
                        except Exception as e:
                            print(f"删除文件失败: {file_info['path']}, 错误: {e}")
                
                print(f"目录删除完成: cicd/{project_id}/{directory_path}, 共删除 {deleted_count} 个文件")
                return True
            else:
                print(f"获取目录文件列表失败: cicd/{project_id}/{directory_path}, 响应: {response.text}")
                return False
                
        except Exception as e:
            print(f"删除目录失败: cicd/{project_id}/{directory_path}, 错误: {e}")
            return False

# 全局GitLab客户端实例
gitlab_client = GitLabClient() 