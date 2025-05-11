// Main JavaScript for Content Planner

document.addEventListener('DOMContentLoaded', function() {
    // Form validation enhancement
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            // Get URL input if it exists
            const urlInput = form.querySelector('input[name="website_url"]');
            if (urlInput && urlInput.value) {
                // Simple URL validation
                if (!isValidUrl(urlInput.value)) {
                    event.preventDefault();
                    showError(urlInput, 'Please enter a valid URL including http:// or https://');
                }
            }
            
            // Get keywords input if it exists
            const keywordsInput = form.querySelector('textarea[name="keywords"]');
            if (keywordsInput && keywordsInput.value) {
                // Check if there's at least one valid keyword
                const keywords = parseKeywords(keywordsInput.value);
                if (keywords.length === 0) {
                    event.preventDefault();
                    showError(keywordsInput, 'Please enter at least one keyword');
                }
            }
        });
    });
    
    // Helper functions
    function isValidUrl(string) {
        try {
            const url = new URL(string);
            return url.protocol === 'http:' || url.protocol === 'https:';
        } catch (_) {
            return false;
        }
    }
    
    function parseKeywords(string) {
        return string.split(/[\n,]/).map(k => k.trim()).filter(k => k.length > 0);
    }
    
    function showError(inputElement, message) {
        // Remove existing error if any
        const existingError = inputElement.parentNode.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }
        
        // Create error message
        const errorElement = document.createElement('p');
        errorElement.className = 'error-message text-red-500 text-xs italic mt-1';
        errorElement.textContent = message;
        
        // Insert after input
        inputElement.parentNode.insertBefore(errorElement, inputElement.nextSibling);
        
        // Highlight input
        inputElement.classList.add('border-red-500');
        
        // Add event listener to clear error on input
        inputElement.addEventListener('input', function() {
            clearError(inputElement);
        }, { once: true });
    }
    
    function clearError(inputElement) {
        // Remove error message
        const errorElement = inputElement.parentNode.querySelector('.error-message');
        if (errorElement) {
            errorElement.remove();
        }
        
        // Remove highlight
        inputElement.classList.remove('border-red-500');
    }
});