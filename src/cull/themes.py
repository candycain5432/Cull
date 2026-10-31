# Color themes, any of these colors can be replaced in the [colors] section of the config
THEMES = {
    "default": {
        "accent": "bold cyan", "heading": "bold", "good": "green", "warn": "yellow", "bad": "red",
        "muted": "dim", "pick": "bold green", "bar": "cyan", "bar_done": "green", "stripe": "on grey11",
    },
    "ocean": {
        "accent": "bold #4cc9f0", "heading": "bold #bde0fe", "good": "#4cc9f0", "warn": "#ffd166", "bad": "#ef476f",
        "muted": "#6c8ead", "pick": "bold #06d6a0", "bar": "#4895ef", "bar_done": "#06d6a0", "stripe": "on #10202e",
    },
    "sunset": {
        "accent": "bold #ff9e64", "heading": "bold #ffd6a5", "good": "#f4b860", "warn": "#ff9e64", "bad": "#f7576c",
        "muted": "#8d7a8f", "pick": "bold #ffcf56", "bar": "#ff6f91", "bar_done": "#ffcf56", "stripe": "on #2a1a26",
    },
    # Blue and orange from the Okabe-Ito palette, so red-green color blindness doesn't hide a score
    "colorblind": {
        "accent": "bold #56b4e9", "heading": "bold", "good": "#56b4e9", "warn": "#f0e442", "bad": "#e69f00",
        "muted": "dim", "pick": "bold #56b4e9", "bar": "#56b4e9", "bar_done": "#56b4e9", "stripe": "on grey11",
    },
    "mono": {
        "accent": "bold", "heading": "bold", "good": "none", "warn": "underline", "bad": "bold reverse",
        "muted": "dim", "pick": "bold", "bar": "none", "bar_done": "bold", "stripe": "on grey11",
    },
}
