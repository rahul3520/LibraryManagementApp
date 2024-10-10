from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, constr
from typing import List, Dict, Optional
import jwt
import datetime

# Secret key for encoding and decoding JWT
SECRET_KEY = "secureKey"  # Change this to a strong secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()

# In-memory user storage
users: Dict[str, Dict[str, str]] = {
    "john_doe": {"password": "securepassword", "role": "LIBRARIAN"},
    "rahul": {"password":"password@123","role":"MEMBER"}
}

# In-memory book storage
books: Dict[int, dict] = {
    1: { "title":"Harry Potter","author":"JK Rowling","description":"series"}
}
next_id = 2

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class UserSignUp(BaseModel):
    username: constr(min_length=3)
    password: constr(min_length=6)
    role: str  # Either 'LIBRARIAN' or 'MEMBER'

class Token(BaseModel):
    access_token: str
    token_type: str

class Book(BaseModel):
    title: str
    author: str
    description: Optional[str] = None

# sign up for new users
@app.post("/signup", response_model=dict)
async def sign_up(user: UserSignUp):
    if user.username in users:
        raise HTTPException(status_code=400, detail="Username already exists")

    if user.role not in ["LIBRARIAN", "MEMBER"]:
        raise HTTPException(status_code=400, detail="Invalid role. Choose 'LIBRARIAN' or 'MEMBER'.")

    users[user.username] = {
        "password": user.password,
        "role": user.role
    }
    
    return {"message": "User registered successfully", "username": user.username}

# get list of librarian or member
@app.get("/users", response_model=List[dict])
async def get_users(role: str = Query(None)):
    if role and role not in ["LIBRARIAN", "MEMBER"]:
        raise HTTPException(status_code=400, detail="Invalid role. Choose 'LIBRARIAN' or 'MEMBER'.")

    filtered_users = [
        {"username": username, "role": data["role"]}
        for username, data in users.items()
        if role is None or data["role"] == role
    ]
    
    return filtered_users

# function to generate jwt token using username
def create_access_token(data: dict, expires_delta: datetime.timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# login url after sign up
@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users.get(form_data.username)
    if not user or user["password"] != form_data.password:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

# url to get user details after login with jwt access token
@app.get("/users/me")
async def read_users_me(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = users.get(username)
    if user is None:
        raise credentials_exception
    
    return {"username": username, "role": user["role"]}

# add books by librarian
@app.post("/books/", response_model=Book)
async def add_book(book: Book, role: str = Query(...)):
    if role != "LIBRARIAN":
        raise HTTPException(status_code=403, detail="Only librarians can add books")

    global next_id
    book_id = next_id
    books[book_id] = book.dict()
    next_id += 1
    return {**book.dict(),"id":book_id}

# get all books
@app.get("/books/", response_model=List[Book])
async def get_books():
    return [{"id": book_id, **book} for book_id, book in books.items()]

# get book by id
@app.get("/books/{book_id}", response_model=Book)
async def get_book(book_id: int):
    if book_id not in books:
        raise HTTPException(status_code=404, detail="Book not found")
    return {**books[book_id], "id": book_id}


# update book by id by Librarian
@app.put("/books/{book_id}", response_model=Book)
async def update_book(book_id: int, book: Book, role: str = Query(...)):
    if role != "LIBRARIAN":
        raise HTTPException(status_code=403, detail="Only librarians can update books")

    if book_id not in books:
        raise HTTPException(status_code=404, detail="Book not found")
    
    books[book_id] = book.dict()
    return {**book.dict(), "id": book_id}

# delete book by book id by Librarian
@app.delete("/books/{book_id}", status_code=204)
async def delete_book(book_id: int, role: str = Query(...)):
    if role != "LIBRARIAN":
        raise HTTPException(status_code=403, detail="Only librarians can delete books")

    if book_id not in books:
        raise HTTPException(status_code=404, detail="Book not found")
    
    del books[book_id]
    return

# test route
@app.get("/")
async def root():
    return {"message": "Hello World"}