import streamlit as st
from ollama import Client
import json #A tool to translate, let python and AI can talk
import random
import urllib.request
import urllib.parse

#set model
client = Client(
    host='https://api-gateway.netdb.csie.ncku.edu.tw', 
    headers={'Authorization': 'Bearer df00bbf401aaa607fbfb103e99b3822188c9ad280b1f966e7f2ed4fef973e039'} 
)

#title
st.title("COOL COOL の Alpaca")

#if here is no todos, create it
if "todos" not in st.session_state:
    st.session_state.todos = []

def add_task(task_content):
    st.session_state.todos.append(task_content)
    return json.dumps({"status": "success", "message": f"Added: {task_content}", "current_list": st.session_state.todos})

def what_to_eat():
    """
    Randomly select a food type for lunch or dinner.
    Use this tool when the user asks what to eat or needs a food recommendation.
    """
    eat = ["Ramen","Sushi","Donfan","Udon","Rice","bullet","Play LOL dont eat","Play VALORANT dont eat"]
    result = random.choice(eat)
    return json.dumps({"status": "success", "Eat": result})

def game_recommend():
    """
    Fetch current best game deals from Steam.
    Use this tool when the user asks for:
    - Game recommendations
    - Best deals or top-rated games
    - "What should I play?"
    - "Can you recommand me some games?"
    """
    try:
        url = "https://www.cheapshark.com/api/1.0/deals?storeID=1&sortBy=Metacritic&pageSize=100"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())

        if not data:
            return json.dumps({"status": "error", "message": "No deals found on Steam right now."})    

        random_picks = random.sample(data, min(len(data), 3))

        game_list = []
        for game in random_picks:
            #get the socre
            score = game.get('metacriticScore', 'N/A')
            game_info = f"Score {score} | Game: {game['title']} (Price ${game['normalPrice']})"
            game_list.append(game_info)
            
        return json.dumps({"status": "success", "recommendations": game_list})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Fail: {str(e)}"})
    
def game_price(game_name):
    """
    Search for the current price of a specific game on Steam.
    Use this tool when the user asks for the price of a specific game (e.g., "How much is Elden Ring?").
    And reply the price of it.
    """
    try:
        encoded_name = urllib.parse.quote(game_name)
        url_2 = f"https://www.cheapshark.com/api/1.0/deals?storeID=1&title={encoded_name}"
        with urllib.request.urlopen(url_2) as response:
            answer = json.loads(response.read().decode())
        if not answer:
            return json.dumps({"status": "empty", "message": f"Cant find:{game_name}, please try again"})
        
        top_results = answer[:3]
        
        game_list_2 = []
        for game in top_results:
            savings = float(game['savings'])
            if savings > 0:
                price_info = f"{game['title']} | For sale: ${game['salePrice']} (Normal price ${game['normalPrice']}, -{savings:.0f}%)"
            else:
                price_info = f"{game['title']} | Current price: ${game['normalPrice']} (No sale)"
            game_list_2.append(price_info)
            
        return json.dumps({"status": "success", "results": game_list_2})
        
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Fail to search: {str(e)}"})

def get_tasks():
    if not st.session_state.todos:
        return json.dumps({"status": "empty", "message": "There is no TO-Do list"})
    return json.dumps({"status": "success", "tasks": st.session_state.todos})

def delete_task(task_content):
    if task_content in st.session_state.todos:
        st.session_state.todos.remove(task_content)
        return json.dumps({"status": "success", "message": f"Deleted: {task_content}"})
    return json.dumps({"status": "error", "message": "Cant find mission"})


#if here is no message, create it
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "Good morning, how can I help you?"}]

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user", avatar="user.png").write(msg["content"])
    elif msg["role"] == "assistant":
        st.chat_message("assistant", avatar="Ollama.png").write(msg["content"])

#deal with input
if prompt := st.chat_input("Please write some instructions......"):
    #echo input
    st.chat_message("user", avatar="user.png").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # call Ollama
    response = client.chat(
        model='gpt-oss:120b', 
        messages=st.session_state.messages,
        tools=[add_task, get_tasks, delete_task, what_to_eat, game_recommend, game_price]
    )

    #check if needs the tool
    if response.get('message', {}).get('tool_calls'):
        st.session_state.messages.append(response['message'])
        
        #do the tool
        for tool in response['message']['tool_calls']:
            function_name = tool['function']['name']
            args = tool['function']['arguments']
            
            tool_result = ""
            if function_name == 'add_task':
                tool_result = add_task(args.get('task_content'))
            elif function_name == 'get_tasks':
                tool_result = get_tasks()
            elif function_name == 'delete_task':
                tool_result = delete_task(args.get('task_content'))
            elif function_name == 'what_to_eat':
                tool_result = what_to_eat()
            elif function_name == 'game_recommend':
                tool_result = game_recommend() 
            elif function_name == 'game_price':
                game_name = args.get('game_name')
                tool_result = game_price(game_name) 
            
            #add record
            st.session_state.messages.append({
                'role': 'tool',
                'content': tool_result,
                'name': function_name
            })
            
            #working
            with st.status(f"Agent now using tool: {function_name}...", expanded=False) as status:
                status.write(f"Argument : {args}")
                status.write(f"Result : {tool_result}")
                status.update(label="Done", state="complete")

        #let AI recieve the result and talk
        final_response = client.chat(
            model='gpt-oss:120b',
            messages=st.session_state.messages
        )
        ai_reply = final_response['message']['content']
        st.chat_message("assistant", avatar="Ollama.png").write(ai_reply)
        st.session_state.messages.append(final_response['message'])

    else:
        #no need tools
        ai_reply = response['message']['content']
        st.chat_message("assistant", avatar="Ollama.png").write(ai_reply)
        st.session_state.messages.append(response['message'])