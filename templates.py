# Meme templates database
# Each template: (image_url, top_text_y, bottom_text_y, max_width)

TEMPLATES = {
    "drake": {
        "name": "Drake Hotline Bling",
        "url": "https://i.imgflip.com/30b1gx.jpg",
        "top_y": 50,      # Y position for top text
        "bottom_y": 450,   # Y position for bottom text  
        "max_width": 450
    },
    "distracted": {
        "name": "Distracted Boyfriend",
        "url": "https://i.imgflip.com/1ur9b0.jpg",
        "top_y": 60,
        "bottom_y": 480,
        "max_width": 500
    },
    "two_buttons": {
        "name": "Two Buttons",
        "url": "https://i.imgflip.com/1g8my4.jpg",
        "top_y": 70,
        "bottom_y": 520,
        "max_width": 480
    },
    "change_mind": {
        "name": "Change My Mind",
        "url": "https://i.imgflip.com/24y43o.jpg",
        "top_y": 80,
        "bottom_y": 540,
        "max_width": 450
    },
    "disaster_girl": {
        "name": "Disaster Girl",
        "url": "https://i.imgflip.com/23ls.jpg",
        "top_y": 40,
        "bottom_y": 430,
        "max_width": 460
    }
}

def get_all_templates():
    """Return list of available template names"""
    return list(TEMPLATES.keys())

def get_template(template_name):
    """Get template by name"""
    return TEMPLATES.get(template_name)
