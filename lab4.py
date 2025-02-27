import sys
import re
import json
from datetime import datetime

# Global variable for MongoDB availability
MONGODB_AVAILABLE = False

try:
    from pymongo import MongoClient
    MONGODB_AVAILABLE = True
except ImportError:
    print("Warning: pymongo not installed. Running in memory-only mode.", file=sys.stderr)

# In-memory database for when MongoDB is not available
in_memory_db = {
    "blogs": {}
}

def parse_quoted_string(line):
    """Parse a quoted string from the input line and return the string and the rest of the line."""
    match = re.match(r'"([^"]*)"(.*)', line.strip())
    if match:
        return match.group(1), match.group(2).strip()
    return "", line.strip()

def process_post(line, db):
    """Process a post command."""
    global MONGODB_AVAILABLE
    
    parts = line.split(' ', 3)
    if len(parts) < 4:
        print("Error: Invalid post command format", file=sys.stderr)
        return
    
    blogname = parts[1]
    username = parts[2].strip('"')
    rest = parts[3]
    
    title, rest = parse_quoted_string(rest)
    body, rest = parse_quoted_string(rest)
    tags, timestamp = parse_quoted_string(rest)
    
    # Create permalink
    permalink = blogname + '.' + re.sub('[^0-9a-zA-Z]+', '_', title)
    
    # Create post document
    post = {
        "type": "post",
        "blogname": blogname,
        "userName": username,
        "title": title,
        "body": body,
        "permalink": permalink,
        "timestamp": timestamp
    }
    
    # Add tags if they exist
    if tags:
        post["tags"] = [tag.strip() for tag in tags.split(',')]
    
    # Insert into database
    if MONGODB_AVAILABLE:
        db.blogs.insert_one(post)
    else:
        # Ensure blog exists in in-memory db
        if blogname not in in_memory_db["blogs"]:
            in_memory_db["blogs"][blogname] = []
        in_memory_db["blogs"][blogname].append(post)

def process_comment(line, db):
    """Process a comment command."""
    global MONGODB_AVAILABLE
    
    parts = line.split(' ', 3)
    if len(parts) < 4:
        print("Error: Invalid comment command format", file=sys.stderr)
        return
    
    blogname = parts[1]
    permalink = parts[2]
    username = parts[3].strip('"')
    
    # Extract the comment body and timestamp
    rest = ' '.join(parts[3:])
    username, rest = parse_quoted_string(rest)
    comment_body, timestamp = parse_quoted_string(rest)
    
    # Check if the referenced post or comment exists
    parent = None
    if MONGODB_AVAILABLE:
        parent = db.blogs.find_one({"permalink": permalink})
    else:
        # Look for parent in in-memory db
        if blogname in in_memory_db["blogs"]:
            for doc in in_memory_db["blogs"][blogname]:
                if doc.get("permalink") == permalink:
                    parent = doc
                    break
    
    if not parent:
        print(f"Error: No post or comment found with permalink: {permalink}", file=sys.stderr)
        return
    
    # Create comment document
    comment = {
        "type": "comment",
        "blogname": blogname,
        "userName": username,
        "body": comment_body,
        "permalink": timestamp,  # Use timestamp as permalink for comments
        "parent_permalink": permalink,
        "timestamp": timestamp
    }
    
    # Insert into database
    if MONGODB_AVAILABLE:
        db.blogs.insert_one(comment)
    else:
        if blogname not in in_memory_db["blogs"]:
            in_memory_db["blogs"][blogname] = []
        in_memory_db["blogs"][blogname].append(comment)

def process_delete(line, db):
    """Process a delete command."""
    global MONGODB_AVAILABLE
    
    parts = line.split(' ', 4)
    if len(parts) < 5:
        print("Error: Invalid delete command format", file=sys.stderr)
        return
    
    blogname = parts[1]
    permalink = parts[2]
    username = parts[3]
    timestamp = parts[4]
    
    # Check if the referenced post or comment exists
    doc = None
    if MONGODB_AVAILABLE:
        doc = db.blogs.find_one({"permalink": permalink})
        if not doc:
            print(f"Error: No post or comment found with permalink: {permalink}", file=sys.stderr)
            return
            
        # Update the document to mark it as deleted
        doc_type = doc.get("type", "post")
        db.blogs.update_one(
            {"permalink": permalink},
            {
                "$set": {
                    "body": f"**{doc_type} deleted**",
                    "deleted_by": username,
                    "deleted_at": timestamp
                }
            }
        )
    else:
        # Handle in-memory deletion
        if blogname in in_memory_db["blogs"]:
            for i, doc in enumerate(in_memory_db["blogs"][blogname]):
                if doc.get("permalink") == permalink:
                    doc_type = doc.get("type", "post")
                    in_memory_db["blogs"][blogname][i]["body"] = f"**{doc_type} deleted**"
                    in_memory_db["blogs"][blogname][i]["deleted_by"] = username
                    in_memory_db["blogs"][blogname][i]["deleted_at"] = timestamp
                    return
                    
        print(f"Error: No post or comment found with permalink: {permalink}", file=sys.stderr)

def get_posts_and_comments(blogname, db):
    """Get all posts and comments for a blog."""
    global MONGODB_AVAILABLE
    
    if MONGODB_AVAILABLE:
        # Find all posts in the blog
        posts = list(db.blogs.find({"blogname": blogname, "type": "post"}).sort("timestamp", -1))
        
        # Find all comments
        comments = list(db.blogs.find({"blogname": blogname, "type": "comment"}).sort("timestamp", 1))
        
        # Organize comments by parent permalink
        comments_by_parent = {}
        for comment in comments:
            parent = comment.get("parent_permalink")
            if parent not in comments_by_parent:
                comments_by_parent[parent] = []
            comments_by_parent[parent].append(comment)
            
        return posts, comments_by_parent
    else:
        # Handle in-memory data
        if blogname not in in_memory_db["blogs"]:
            return [], {}
            
        posts = [doc for doc in in_memory_db["blogs"][blogname] if doc.get("type") == "post"]
        # Sort posts by timestamp in descending order
        posts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        comments = [doc for doc in in_memory_db["blogs"][blogname] if doc.get("type") == "comment"]
        # Sort comments by timestamp in ascending order
        comments.sort(key=lambda x: x.get("timestamp", ""))
        
        # Organize comments by parent permalink
        comments_by_parent = {}
        for comment in comments:
            parent = comment.get("parent_permalink")
            if parent not in comments_by_parent:
                comments_by_parent[parent] = []
            comments_by_parent[parent].append(comment)
            
        return posts, comments_by_parent

def process_show(line, db):
    """Process a show command."""
    parts = line.split(' ', 1)
    if len(parts) < 2:
        print("Error: Invalid show command format", file=sys.stderr)
        return
    
    blogname = parts[1].strip()
    
    print(f"in {blogname}:")
    print()
    
    posts, comments_by_parent = get_posts_and_comments(blogname, db)
    
    for post in posts:
        print("  - - - -")
        print(f"\ttitle: {post.get('title', '')}")
        print(f"\tuserName: {post.get('userName', '')}")
        
        if "tags" in post and post["tags"]:
            print(f"\ttags: {', '.join(post['tags'])}")
            
        print(f"\ttimestamp: {post.get('timestamp', '')}")
        print(f"\tpermalink: {post.get('permalink', '')}")
        
        if "deleted_by" in post:
            print(f"\tbody:\n\t  **post deleted**")
        else:
            print(f"\tbody:\n\t  {post.get('body', '')}")
        
        # Print comments for this post
        print_comments(post.get("permalink"), comments_by_parent, indent=1)
        print()

def print_comments(permalink, comments_by_parent, indent=0):
    """Recursively print comments and their replies."""
    indent_str = "  " * indent
    
    if permalink not in comments_by_parent:
        return
        
    for comment in comments_by_parent[permalink]:
        print()
        print(f"{indent_str}    - - - -")
        print(f"{indent_str}\tuserName: {comment.get('userName', '')}")
        print(f"{indent_str}\tpermalink: {comment.get('permalink', '')}")
        
        if "deleted_by" in comment:
            print(f"{indent_str}\tcomment:\n{indent_str}\t  **comment deleted**")
        else:
            print(f"{indent_str}\tcomment:\n{indent_str}\t  {comment.get('body', '')}")
        
        # Print replies to this comment
        print_comments(comment["permalink"], comments_by_parent, indent + 1)

def process_find(line, db):
    """Process a find command (Extra Credit)."""
    global MONGODB_AVAILABLE
    
    parts = line.split(' ', 2)
    if len(parts) < 3:
        print("Error: Invalid find command format", file=sys.stderr)
        return
    
    blogname = parts[1]
    search_string, _ = parse_quoted_string(parts[2])
    
    print(f"in {blogname}:")
    print()
    
    if MONGODB_AVAILABLE:
        # Search in post bodies, tags, and comment bodies
        query = {
            "blogname": blogname,
            "$or": [
                {"body": {"$regex": search_string}},
                {"tags": search_string},
            ]
        }
        
        results = db.blogs.find(query).sort("timestamp", -1)
        
        for doc in results:
            if doc["type"] == "post":
                print("  - - - -")
                print(f"\ttitle: {doc.get('title', '')}")
                print(f"\tuserName: {doc.get('userName', '')}")
                
                if "tags" in doc and doc["tags"]:
                    print(f"\ttags: {', '.join(doc['tags'])}")
                    
                print(f"\ttimestamp: {doc.get('timestamp', '')}")
                print(f"\tpermalink: {doc.get('permalink', '')}")
                
                if "deleted_by" in doc:
                    print(f"\tbody:\n\t  **post deleted**")
                else:
                    print(f"\tbody:\n\t  {doc.get('body', '')}")
                
                # Find and print matching comments
                matching_comments = db.blogs.find({
                    "parent_permalink": doc["permalink"],
                    "type": "comment",
                    "body": {"$regex": search_string}
                }).sort("timestamp", 1)
                
                comments_by_parent = {}
                for comment in matching_comments:
                    parent = comment.get("parent_permalink")
                    if parent not in comments_by_parent:
                        comments_by_parent[parent] = []
                    comments_by_parent[parent].append(comment)
                
                print_comments(doc["permalink"], comments_by_parent, indent=1)
                print()
            elif doc["type"] == "comment":
                # Print comment without its parent post
                print("  - - - -")
                print(f"\tuserName: {doc.get('userName', '')}")
                print(f"\tpermalink: {doc.get('permalink', '')}")
                
                if "deleted_by" in doc:
                    print(f"\tcomment:\n\t  **comment deleted**")
                else:
                    print(f"\tcomment:\n\t  {doc.get('body', '')}")
                print()
    else:
        # Handle in-memory search
        if blogname not in in_memory_db["blogs"]:
            return
            
        posts, comments_by_parent = get_posts_and_comments(blogname, db)
        
        # Filter posts and comments containing the search string
        for post in posts:
            found_in_post = False
            matching_comments = {}
            
            # Check post body
            if search_string in post.get("body", ""):
                found_in_post = True
                
            # Check tags
            if "tags" in post and any(search_string in tag for tag in post["tags"]):
                found_in_post = True
                
            # Check comments for this post
            post_permalink = post.get("permalink")
            if post_permalink in comments_by_parent:
                for comment in comments_by_parent[post_permalink]:
                    if search_string in comment.get("body", ""):
                        if post_permalink not in matching_comments:
                            matching_comments[post_permalink] = []
                        matching_comments[post_permalink].append(comment)
            
            if found_in_post:
                # Print post details
                print("  - - - -")
                print(f"\ttitle: {post.get('title', '')}")
                print(f"\tuserName: {post.get('userName', '')}")
                
                if "tags" in post and post["tags"]:
                    print(f"\ttags: {', '.join(post['tags'])}")
                    
                print(f"\ttimestamp: {post.get('timestamp', '')}")
                print(f"\tpermalink: {post.get('permalink', '')}")
                
                if "deleted_by" in post:
                    print(f"\tbody:\n\t  **post deleted**")
                else:
                    print(f"\tbody:\n\t  {post.get('body', '')}")
                
                # Print matching comments
                if post_permalink in matching_comments:
                    for comment in matching_comments[post_permalink]:
                        print()
                        print(f"    - - - -")
                        print(f"\tuserName: {comment.get('userName', '')}")
                        print(f"\tpermalink: {comment.get('permalink', '')}")
                        
                        if "deleted_by" in comment:
                            print(f"\tcomment:\n\t  **comment deleted**")
                        else:
                            print(f"\tcomment:\n\t  {comment.get('body', '')}")
                print()

def main():
    global MONGODB_AVAILABLE
    
    # Initialize DB connection
    db = None
    if MONGODB_AVAILABLE:
        try:
            # Try to connect to MongoDB without authentication
            client = MongoClient("mongodb://localhost:27017/")
            db = client["blogdb"]
            # Test connection
            db.command("ping")
            print("Connected to MongoDB", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Could not connect to MongoDB: {e}", file=sys.stderr)
            print("Running in memory-only mode", file=sys.stderr)
            MONGODB_AVAILABLE = False
    
    # Process commands from stdin
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        parts = line.split(' ', 1)
        command = parts[0].lower()
        
        if command == "post":
            process_post(line, db)
        elif command == "comment":
            process_comment(line, db)
        elif command == "delete":
            process_delete(line, db)
        elif command == "show":
            process_show(line, db)
        elif command == "find":
            process_find(line, db)
        else:
            print(f"Error: Unknown command: {command}", file=sys.stderr)

if __name__ == "__main__":
    main()
