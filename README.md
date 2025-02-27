# MongoDB Blogging App

This application implements a MongoDB-based blog engine that processes commands to create, comment on, delete, and display blog posts.

## Prerequisites

- Python 3.x
- PyMongo package (optional - application can run without MongoDB)
- MongoDB (optional - application will use in-memory storage if MongoDB is unavailable)

## Installation

1. Install the PyMongo package:
   ```bash
   pip install pymongo
   ```

2. Configure MongoDB (if using):
   - Install MongoDB from the official website or package manager
   - Start the MongoDB service:
     ```bash
     # Linux
     sudo systemctl start mongodb
     
     # macOS
     brew services start mongodb-community
     
     # Windows
     # MongoDB runs as a service after installation
     ```
   
3. Edit the `config.ini` file with your MongoDB credentials:
   ```ini
   [MongoDB]
   host = localhost
   port = 27017
   database = blogdb
   username = your_username
   password = your_password
   ```
   Note: For local MongoDB installations without authentication, you can leave username and password empty.

## Running the Application

### Interactive Mode
Run the application and type commands directly:
```bash
python lab4.py
```

### File Input Mode
Process commands from a file:
```bash
python lab4.py < inputfile.txt > outputfile.txt 2>&1
```

## Supported Commands and Examples

### Post
Creates a new blog post.
```
post blogName userName title postBody tags timestamp
```

Example:
```
post technology "JaneDoe" "The Future of AI" "This article discusses recent advancements in artificial intelligence and machine learning." "AI,machine learning,technology" 2023-05-15T14:30:22.123Z
```

### Comment
Adds a comment to an existing post or comment.
```
comment blogname permalink userName commentBody timestamp
```

Example (comment on a post):
```
comment technology technology.The_Future_of_AI "JohnSmith" "Great article! I think quantum computing will accelerate AI even further." 2023-05-16T09:12:45.789Z
```

Example (comment on a comment):
```
comment technology 2023-05-16T09:12:45.789Z "AlanTuring" "I agree with John. Quantum computing will revolutionize the field." 2023-05-16T10:22:33.456Z
```

### Delete
Marks a post or comment as deleted.
```
delete blogname permalink userName timestamp
```

Example:
```
delete technology 2023-05-16T10:22:33.456Z "AlanTuring" 2023-05-17T08:05:12.345Z
```

### Show
Displays all posts and comments in a blog.
```
show blogName
```

Example:
```
show technology
```

### Find
Searches for posts and comments containing a specific string.
```
find blogName searchString
```

Example:
```
find technology "quantum"
```

## Important Notes on Command Ordering

1. You must create a post before commenting on it
2. You must create a comment before commenting on it
3. You must create a post or comment before deleting it
4. Permalink references must point to existing entities

## Verifying Data in MongoDB

If you're using MongoDB and want to check the data directly:

```bash
mongo
use blogdb
db.blogs.find()
```

## Testing

The application includes test files:
- `testfile1.in`: Sample input commands in French
- `testfile1.out`: Expected output for the sample input

To test the application:
```bash
python lab4.py < testfile1.in > grader.testfile1.out 2>&1
diff grader.testfile1.out testfile1.out
```

## Implementation Notes

- The application automatically falls back to an in-memory database if MongoDB is not available
- The permalink for posts is created by replacing all non-alphanumeric characters in the title with underscores and prepending the blog name
- Comments have the timestamp as their permalink
- When a post or comment is deleted, it's marked as deleted but not removed from the database
- The application handles non-English characters (French in test examples)
