import ImageGenerator as generator


def main():
    generator.init()
    generator.replace("text", "ينا الألم. في بعض الأحيان ونظراً للالتزامات التي يفرضها علينا الواجب والعمل سنتنازل غالباً ونرفض الشعور")
    generator.replace("handle", "@user123")
    generator.replace("displayname", "Example User")
    generator.replace("pfpurl", "https://picsum.photos/500")
    generator.screenshot("example.png")


if __name__ == "__main__":
    main()
