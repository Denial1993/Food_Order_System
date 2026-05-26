"""
重設管理員密碼小工具（不用 reset 整個 DB）

用法：
    cd backend
    venv\\Scripts\\python.exe reset_admin_password.py admin admin123
    venv\\Scripts\\python.exe reset_admin_password.py 帳號 新密碼

若帳號不存在會自動建立一個 UserType='S' 的管理員。
"""
import sys

from core.security import hash_password
from database import SessionLocal
from models import FoodRole, FoodUser


def main() -> None:
    if len(sys.argv) != 3:
        print("用法: python reset_admin_password.py <account> <new_password>")
        sys.exit(1)

    account, new_pwd = sys.argv[1], sys.argv[2]
    db = SessionLocal()
    try:
        user = db.query(FoodUser).filter(FoodUser.Account == account).first()
        if user:
            user.Password = hash_password(new_pwd)
            user.StatusCode = "111"        # 順便確保啟用
            user.UserType = "S"
            print(f"[updated] {account} 密碼已重設")
        else:
            # 找一個角色當預設（沒有就用 NULL）
            role = db.query(FoodRole).filter(FoodRole.StatusCode == "111").first()
            user = FoodUser(
                Account=account,
                Password=hash_password(new_pwd),
                UserName=account,
                UserType="S",
                RoleID=role.RoleID if role else None,
                StatusCode="111",
                AddUser="reset_tool",
            )
            db.add(user)
            print(f"[created] {account} 已建立")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
