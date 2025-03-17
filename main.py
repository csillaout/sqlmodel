from operator import is_
from fastapi import FastAPI, status, HTTPException
from sqlmodel import SQLModel, Session, select, or_
from models import Category, CategoryBase, Video, VideoBase, CategorizedVideos
from database import engine
from fastapi.responses import HTMLResponse
import uvicorn
from typing import List
from datetime import datetime

#Define main app name and database session name
app = FastAPI()

#this connect the db with the engine
session = Session(bind=engine)

#Routes
#Root folder (home page)
@app.get('/', response_class=HTMLResponse)
async def home():
    return '''
    <h1>Home Page</h1>
    <a href='http://127.0.0.1:8000/docs'>Swagger UI: http://127.0.0.1:8000/docs</a>
    '''
#region video_routers

#Post new video
@app.post('/video', status_code=status.HTTP_201_CREATED)
async def post_a_video(video:VideoBase):
    # Create a new video object from data passed in
    new_video = Video(**video.model_dump())
    # Make sure new video has a valid category is:
    if not await is_category_id(new_video.category_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = "No such category")
    # Post the video
    with Session(engine) as session:
        session.add(new_video)
        session.commit()
        session.refresh(new_video)
    return new_video

#Delete one video
@app.delete('/video/{video_id}')
async def delete_a_video(video_id:int):
    if not await is_active_video(video_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = "No such video")
    with Session(engine) as session:
        #Get  the video to delete
        video = session.get(Video, video_id)
        #Set is_active to False, and update date last changed
        video.is_active =False
        video.date_last_changed = datetime.utcnow()
        session.commit()
    return {'Deleted': video_id}

#Undelete one video by changing is_active to True
@app.delete('/undelete/{video_id}')
async def undelete_a_video(video_id:int):
    with Session(engine) as session:
        #Get  the video to restore
        video = session.get(Video, video_id)
        if not video:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = "No such video")
        #Set is_active to True, and update date last changed
        video.is_active =True
        video.date_last_changed = datetime.utcnow()
        session.commit()
    return {'Restore': video_id}

# Get all active videos
@app.get('/video', response_model=List[Video])
async def get_all_videos():
    with Session(engine) as session:
        # Include only videos where is_active is True
        statement = select(Video).where(Video.is_active == True).order_by(Video.title)   
        #select(Category).where(Category.id >=2) retrieve any category where id is higher than 2
        #select(Category).where(Category.name.like('C%)) retrieve any category where name start with C
        # select(Category).where(Category.name.like('%s%)) would retrieve any category name that has s in it
        #select(Category).where(Category.name.like('%script')) retrieve any world ends with script
        #select(Category).where(Category.name.like('HTM_')) returns any word starts with HTM
        #select(Category).where(or_(Category.id==1, Category.id==3)) returns any word that has id 1 or 3
        # select(Category).where(or_(Category.name=='HTML', Category.name=='Java')) return any word has HTML or Java
        result = session.exec(statement)
        all_videos = result.all()
    return all_videos

# Get one video, but only if it is active
@app.get('/video/{video_id}', response_model=VideoBase)
async def get_a_video(video_id: int):
    #Return error if no active video with that id
    if not await is_active_video(video_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active video with that ID")
    video = session.get(Video, video_id)
    return video

# Update one video
@app.put('/video/{video_id}', response_model=Video)
async def update_a_video(video_id: int, update_video: VideoBase):
    # Block if original video not found or inactive
    if not await is_active_video(video_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such video")
    
    # Block if the new category ID is invalid
    if not await is_category_id(update_video.category_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid category id")

    # Otherwise, update the existing video
    with Session(engine) as session:
        # Retrieve the original video
        original_video = session.get(Video, video_id)
        
        if not original_video:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such video")

        # Get dictionary so we can loop through fields (exclude unset fields)
        video_dict = update_video.model_dump(exclude_unset=True)

        # Loop through fields and update
        for key, value in video_dict.items():
            setattr(original_video, key, value)

        # Update the last changed date
        original_video.date_last_changed = datetime.utcnow()

        session.commit()
        session.refresh(original_video)

        return original_video
#endregion

#region category_routers
#Root folder (category)
@app.get('/category', response_model=List[Category])
async def get_all_categories():
    with Session(engine) as session:
        statement = select(Category).order_by(Category.id.desc())   
        #select(Category).where(Category.id >=2) retrieve any category where id is higher than 2
        #select(Category).where(Category.name.like('C%)) retrieve any category where name start with C
        # select(Category).where(Category.name.like('%s%)) would retrieve any category name that has s in it
        #select(Category).where(Category.name.like('%script')) retrieve any world ends with script
        #select(Category).where(Category.name.like('HTM_')) returns any word starts with HTM
        #select(Category).where(or_(Category.id==1, Category.id==3)) returns any word that has id 1 or 3
        # select(Category).where(or_(Category.name=='HTML', Category.name=='Java')) return any word has HTML or Java
        result = session.exec(statement)
        all_categories = result.all()
    return all_categories

#Post a new category
@app.post('/category', status_code=status.HTTP_201_CREATED)
async def post_a_category(category:CategoryBase):
    if await is_category_name(category.name):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Category name already in use")
    new_category = Category(name=category.name)
    with Session(engine) as session:
        session.add(new_category)
        session.commit()
        session.refresh(new_category)
    return new_category

#Get one categories
@app.get('/category/{category_id}', response_model=Category)
async def post_a_category(category_id:int):
    if not await is_category_id(category_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = "No such category")
    with Session(engine) as session:
        #Alternative syntax when getting one row by id
        category = session.get(Category, category_id)
    return category


#Update one category
@app.put('/category/{category_id}', response_model=Category)
async def update_a_category(category_id:int, category:CategoryBase):
    if not await is_category_id(category_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = "No such category")
    with Session(engine) as session:
        #Get current category object form table
        current_category = session.get(Category, category_id)
        #Replace current category name with the one just passed in
        current_category.name = category.name
        #Put back in table with new name
        session.add(current_category)
        session.commit()
        session.refresh(current_category)
    return current_category

#Delete one category
@app.delete('/category/{category_id}')
async def delete_a_category(category_id:int):
    if not await is_category_id(category_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = "No such category")
    #Dont allow them to delete category if it contains active videos
    if await count_videos_in_category(category_id)>0:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail = "Can't delete category that contains active videos")
    with Session(engine) as session:
        #Get current category object form table
        category = session.get(Category, category_id)
        #Delete the category
        session.delete(category)
        session.commit()
    return {'Deleted':category_id}
#endregion

#region joins
@app.get('/categorized_video', response_model=List[CategorizedVideos])
async def get_categorized_videos():
    with Session(engine) as session:
        # Execute query and fetch results
        cat_vids = session.exec(
            select(Video.id, Category.name, Video.title, Video.youtube_code)
            .join(Category)
            .where(Video.is_active)
            .order_by(Category.name, Video.title)
        ).all()
    return [
    {
        "id": video_id, 
        "category": name, 
        "title": title, 
        "youtube_code": code
    }
    for video_id, name, title, code in cat_vids
]

#endregion

#region validators
#returns True if category id exists, otherwise returns False(server side validation)
async def is_category_id(category_id:int):
    if not session.get(Category, category_id):
        return False
    return True

#returns True if category name exists, otherwise returns False(server side validation)
async def is_category_name(category_name:str):
    with Session(engine) as session:
        category = session.exec(select(Category).where(Category.name == category_name)).one_or_none()
        return category is not None

#returns True if video id exists and is_active is True, otherwise returns False(server side validation)
async def is_active_video(video_id: int):
    if session.exec(
        #Select where video id is valid and is_active is True
        select(Video).where(Video.id == video_id, Video.is_active)
    ).one_or_none():
        return True
    return False

#returns the number of active videos in any category 
async def count_videos_in_category(category_id:int):
    rows=session.exec(
        select(Video.category_id).where(Video.category_id==category_id).where(Video.is_active)
    ).all()
    return len(rows)

# endregion

# for debugging with breakpoints in VS Code
if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)