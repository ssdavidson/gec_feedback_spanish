document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('feedback-form');
    const feedbackResult = document.getElementById('feedback-result');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const inputText = document.getElementById('input-text').value;
        const level = parseInt(document.getElementById('level').value);
        const nativeLanguage = document.getElementById('native-language').value;

        try {
            const response = await fetch('/api/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    input_string: inputText,
                    level: level,
                    native_language: nativeLanguage
                })
            });

            if (response.ok) {
                const data = await response.json();
                feedbackResult.innerHTML = `Feedback: ${data.feedback}`;
                //Update this to iterate through the feedback dynamically based system settings.
            } else {
                feedbackResult.innerHTML = 'Error fetching feedback. Please try again later.';
            }
        } catch (error) {
            console.error('Error:', error);
            feedbackResult.innerHTML = 'An unexpected error occurred. Please try again later.';
        }
    });
});