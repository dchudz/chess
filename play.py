import chess
import os
import openai
import time
import json
import chess.svg
import tempfile
import webbrowser
from pathlib import Path

# Initialize OpenAI client
api_key = os.environ.get("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set. Please set it before running the program.")
client = openai.OpenAI(api_key=api_key)
    
def display_board(board, title="Chess Board"):
    """Display the chess board as an SVG image in the default web browser"""
    # Create SVG representation of the board
    svg_content = chess.svg.board(board=board, size=400)
    
    # Create a temporary HTML file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as f:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; }}
                h1 {{ color: #333; }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            {svg_content}
        </body>
        </html>
        """
        f.write(html_content.encode('utf-8'))
        filename = f.name
    
    # Open the HTML file in the default web browser
    webbrowser.open('file://' + filename)
    print(f"Board displayed in browser: {filename}")

def get_gpt4_move(board, move_history):
    """Ask GPT-4o to make a chess move using function calling"""
    # Create a prompt with the move history
    move_string = ""
    for i, move in enumerate(move_history):
        if i % 2 == 0:  # White's move
            move_string += f"{(i//2)+1}. {move} "
        else:  # Black's move
            move_string += f"{move} "
    
    # Add the move number for the current move if it's white's turn
    if board.turn == chess.WHITE and move_history:
        move_string += f"{(len(move_history)//2)+1}. "
    
    # Get list of legal moves in SAN notation
    legal_moves_san = [board.san(move) for move in board.legal_moves]
    
    # Create the prompt
    prompt = f"Let's play chess. {move_string}"
    
    # Print the prompt being sent to GPT-4o
    print("\n--- Prompt sent to GPT-4o ---")
    print(prompt)
    print("--- End of prompt ---\n")
    
    # Define the function for GPT to call
    functions = [
        {
            "type": "function",
            "function": {
                "name": "make_chess_move",
                "description": "Make a chess move",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "move": {
                            "type": "string",
                            "enum": legal_moves_san,
                            "description": "The chess move in Standard Algebraic Notation (SAN)"
                        }
                    },
                    "required": ["move"]
                }
            }
        }
    ]
    
    # Call the OpenAI API with function calling
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            tools=functions,
            tool_choice={"type": "function", "function": {"name": "make_chess_move"}},
            temperature=0.7
        )
        
        # Extract the function call
        message = response.choices[0].message
        
        # Get the move from the function call
        if message.tool_calls:
            function_call = message.tool_calls[0].function
            arguments = json.loads(function_call.arguments)
            chosen_move = arguments.get("move")
            
            # Print GPT's response
            print(f"\nGPT-4o says: I choose {chosen_move}")
            
            # Parse the move
            move = board.parse_san(chosen_move)
            return move
        else:
            # Fallback if no function call was made
            print("GPT-4o didn't make a function call. Choosing randomly.")
            return list(board.legal_moves)[0]
    
    except Exception as e:
        print(f"Error getting move from GPT-4o: {e}")
        print("Choosing a random legal move instead.")
        return list(board.legal_moves)[0]

# Main game loop
def play_chess():
    board = chess.Board()
    move_history = []
    
    # Print the initial board
    print("Initial board:")
    print(board)
    display_board(board, "Initial position")
    
    while not board.is_game_over():
        if board.turn == chess.WHITE:
            # Human's turn (white)
            move_input = input("\nEnter your move (e.g. 'e4' or 'e2e4'): ")
            
            try:
                # First try to parse as SAN
                try:
                    move = board.parse_san(move_input)
                except ValueError:
                    # If SAN parsing fails, try UCI notation
                    move = chess.Move.from_uci(move_input)
                    if move not in board.legal_moves:
                        print("\nIllegal move! Try again.")
                        continue
                
                # Make the move
                san_move = board.san(move)
                board.push(move)
                move_history.append(san_move)
                
                print("\nBoard after your move:")
                print(board)
                display_board(board, f"After {san_move}")
                
                if board.is_game_over():
                    break
                
            except ValueError:
                print("\nInvalid move format! Please use standard notation (e.g. 'e4') or UCI notation (e.g. 'e2e4').")
                continue
        else:
            # GPT-4o's turn (black)
            print("\nGPT-4o is thinking...")
            time.sleep(1)  # Add a small delay to make it feel more natural
            
            # Get GPT-4o's move
            move = get_gpt4_move(board, move_history)
            
            # Make the move
            san_move = board.san(move)
            board.push(move)
            move_history.append(san_move)
            
            print(f"\nGPT-4o plays: {san_move}")
            print("\nBoard after GPT-4o's move:")
            print(board)
            display_board(board, f"After {san_move}")
    
    # Game over
    print("\nGame over!")
    result = board.result()
    print(f"Result: {result}")
    
    if result == "1-0":
        print("You (White) won!")
    elif result == "0-1":
        print("GPT-4o (Black) won!")
    else:
        print("It's a draw!")

# Start the game
if __name__ == "__main__":
    try:
        play_chess()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please set your OpenAI API key with: export OPENAI_API_KEY='your-api-key'")
