from flask import Flask, request, jsonify
from feedback_generation import generate_feedback, gec

app = Flask(__name__)

@app.route('/api/feedback', methods=['POST'])
def process_feedback():
    try:
        # Get the input string from the client
        input_data = request.json.get('input_string')

        # Call the generate_feedback function
        l1 = 'english'
        level = '1'
        edits, cor_lines = gec(input_data)
        feedback_response = generate_feedback(edits, l1, level)

        # Create a JSON response
        response_data = {'feedback': feedback_response}
        return jsonify(response_data), 200
    
    except Exception as e:
        # Handle any errors gracefully
        error_message = f"Error processing feedback: {str(e)}"
        return jsonify({'error': error_message}), 500

if __name__ == '__main__':
    app.run(debug=True)