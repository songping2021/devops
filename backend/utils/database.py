#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psycopg2
from psycopg2.extras import RealDictCursor
from backend.config.settings import DB_CONFIG

class DatabaseManager:
    """数据库管理类"""
    
    def __init__(self):
        self.db_config = DB_CONFIG
    
    def get_connection(self):
        """创建数据库连接"""
        return psycopg2.connect(**self.db_config)
    
    def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
        """
        执行查询
        
        Args:
            query: SQL查询语句
            params: 查询参数
            fetch_one: 是否返回单条记录
            fetch_all: 是否返回所有记录
            
        Returns:
            查询结果
        """
        try:
            conn = self.get_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute(query, params)
            
            if fetch_one:
                result = cur.fetchone()
            elif fetch_all:
                result = cur.fetchall()
            else:
                result = None
            
            conn.commit()
            cur.close()
            conn.close()
            
            return result
            
        except Exception as e:
            print(f"数据库操作失败: {e}")
            raise e
    
    def execute_insert(self, query, params=None, return_id=False):
        """
        执行插入操作
        
        Args:
            query: INSERT SQL语句
            params: 插入参数
            return_id: 是否返回插入的ID
            
        Returns:
            插入结果
        """
        try:
            conn = self.get_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            if return_id and "RETURNING" not in query.upper():
                query += " RETURNING *"
            
            cur.execute(query, params)
            
            if return_id or "RETURNING" in query.upper():
                result = cur.fetchone()
            else:
                result = None
            
            conn.commit()
            cur.close()
            conn.close()
            
            return result
            
        except Exception as e:
            print(f"数据库插入失败: {e}")
            raise e
    
    def execute_update(self, query, params=None, return_updated=False):
        """
        执行更新操作
        
        Args:
            query: UPDATE SQL语句
            params: 更新参数
            return_updated: 是否返回更新后的记录
            
        Returns:
            更新结果
        """
        try:
            conn = self.get_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            if return_updated and "RETURNING" not in query.upper():
                query += " RETURNING *"
            
            cur.execute(query, params)
            
            if return_updated or "RETURNING" in query.upper():
                result = cur.fetchone()
            else:
                result = cur.rowcount
            
            conn.commit()
            cur.close()
            conn.close()
            
            return result
            
        except Exception as e:
            print(f"数据库更新失败: {e}")
            raise e
    
    def execute_delete(self, query, params=None, return_deleted=False):
        """
        执行删除操作
        
        Args:
            query: DELETE SQL语句
            params: 删除参数
            return_deleted: 是否返回删除的记录
            
        Returns:
            删除结果
        """
        try:
            conn = self.get_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            if return_deleted and "RETURNING" not in query.upper():
                query += " RETURNING *"
            
            cur.execute(query, params)
            
            if return_deleted or "RETURNING" in query.upper():
                result = cur.fetchone()
            else:
                result = cur.rowcount
            
            conn.commit()
            cur.close()
            conn.close()
            
            return result
            
        except Exception as e:
            print(f"数据库删除失败: {e}")
            raise e

# 全局数据库管理器实例
db_manager = DatabaseManager() 