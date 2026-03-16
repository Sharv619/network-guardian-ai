withfirst week we start with how we used to messs oh this bih runs in my laptop which means it's alright 
npm run dev is all i used to do and then push the code on github and then pull from ec2 instance,
Although being the solodev in this project, it was like a learning curve and my biggest pain point.


that's why i started building codeflow-hook. it started as a simulator (HELLO HACKERS!, just putting my ideas here, if you haveany just add here, man i'd love to get paid by just sitting and doing stuffs on my laptop) 

First thing i built was codeflow-hook, 
which was like whenever i do a git push it just checks for the git diff, if the git diff is larger (since i was vibecoding and trying first on my project) it breaks down in chunks and then does the analysis of each segments. 
i also did EKG in this bih and also gave this project RAG capability to save the data as vector knowledge, so whenever i do a push, it saves how the dev are  pushing the code and then the AI which is offline running in this hook,it also gives you learning pattern (is what im hoping for it to do next)
While i was building this i see another company Rabbit MD makingin the news for AI analysis and when i saw the architecture they are running, they are putting everrything on the model (which was my first phase of this project, which i scrapped even before knowing about this company) i was more focused on offline AI capabilities, what if the AI is running in your CLI just like what ollama does but better, it doesnt forgets about the past because there's this RAG to fallback to and for the AI to read and understand, I believe the thing im makingis more on the side of homelab worthy, that wasalways been a dream, now im focusing more on getting that before i leave this country for good. 




Following codeflow-hook is network guardian which was like this one project, i started working on this project when i saw a google deepmind hackathon, coming back to project i was looking at SRE roles for some company, and thought to myself what if i have a kickass project which i can flex during my interview that look at this log, these are the websites who are trying to access my data XD