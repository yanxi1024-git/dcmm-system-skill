        """)
        
        info["tables"] = [table["name"] for table in tables]
        info["table_count"] = len(tables)
        
        # 获取数据库文件大小
        try:
            file_size = os.path.getsize(self.db_path)
            info["file_size_bytes"] = file_size
            info["file_size_mb"] = round(file_size / (1024 * 1024), 2)
        except:
            info["file_size_bytes"] = 0
            info["file_size_mb"] = 0
        
        # 获取总记录数
        total_records = 0
        for table in info["tables"]:
            try:
                count_result = self.fetch_one(f"SELECT COUNT(*) as count FROM {table}")
                if count_result:
                    total_records += count_result["count"]
            except:
                pass
        
        info["total_records"] = total_records
        
        return info
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info("SQLite数据库连接已关闭")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


# 全局SQLite客户端实例
_sqlite_client: Optional[SQLiteClient] = None

def get_sqlite_client() -> SQLiteClient:
    """获取全局SQLite客户端实例"""
    global _sqlite_client
    if _sqlite_client is None:
        _sqlite_client = SQLiteClient()
    return _sqlite_client


if __name__ == "__main__":
    # 测试SQLite客户端
    with get_sqlite_client() as client:
        # 测试数据库信息
        db_info = client.get_database_info()
        print(f"数据库信息: {db_info}")
        
        # 测试配置操作
        client.set_config("test.config", "test_value", "string", "test", "测试配置")
        config = client.get_config("test.config")
        print(f"测试配置: {config}")
        
        # 测试Token使用记录
        client.record_token_usage("deepseek/deepseek-chat", 100, 50, 150, 0.001)
        token_summary = client.get_token_usage_summary()
        print(f"Token使用摘要: {token_summary}")
        
        print("SQLite客户端测试完成")
