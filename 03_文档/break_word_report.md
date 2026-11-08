# 译语换行拆词 / 标点避头尾 扫描修复报告（jieba 分词判据）

- 语料: `_work/o2_text_zh_full12.tsv`（3844 行）
- 判据 A: jieba 对相邻两行连续分词, token 跨行即拆词
- 判据 B: 标点避头尾（行首禁则 / 行尾禁则）
- 修复: 最小移位 ±1..±3 字符, 行数不变, 行宽不增
- 结果: **修复 21 条**，待人工 0 条

## 自动修复明细

### idx=738 key=2097181444
```
EN: He is using her... He likes that... The filth... The humiliation.  
旧: 他正在利用她…他很享受那个 ⏎ …这肮脏的…屈辱。
新: 他正在利用她…他很享受 ⏎ 那个…这肮脏的…屈辱。
  换行点0 行首标点(…) -> 移位 k=2 …她…他很享受 ⇄ 那个…这肮脏…
```
### idx=1178 key=184578824
```
EN: for an experiment that would save the life ⏎ of his diseased brother, Leonard.
旧: 去进行一项只为拯救他病入膏肓的兄 ⏎ 弟——莱纳德的实验。
新: 去进行一项只为拯救他病入膏肓的 ⏎ 兄弟——莱纳德的实验。
  换行点0 拆词(兄弟) -> 移位 k=1 …他病入膏肓的 ⇄ 兄弟——莱纳…
```
### idx=1287 key=801141001
```
EN: Mei's desk. She's the computer geek of this dorm.
旧: 王梅的书桌 ⏎ 。她是这栋宿舍楼里的电脑怪杰。
新: 王梅的书桌。 ⏎ 她是这栋宿舍楼里的电脑怪杰。
  换行点0 行首标点(。) -> 移位 k=-1 …王梅的书桌。 ⇄ 她是这栋宿舍…
```
### idx=1420 key=419450892
```
EN: Male subject 22 years old, Rh factor O neg. ⏎ Cause of death: Victim bled to death ⏎ after having been cut and raked by ⏎ an unknown weapon [...] ⏎  ⏎ Remarks: The body contains traces ⏎ of an unknown black substance, concentrated ⏎ in the lungs and in the genital area. ⏎  ⏎ The lungs are definitely the first area ⏎ that was exposed to the substance ⏎ (which seems parasitic in nature); ⏎ probably after taking some kind of narcotic ⏎ via the respiratory system. ⏎  ⏎ This death is to be connected with that ⏎ of the girlfriend of the victim. Her lungs ⏎ were completely clean, contrary ⏎ to her reproductive organ. Contagion through ⏎ genital contact with any of the ⏎ bodies mucus membranes (through ⏎ intercourse for example) seems likely ⏎ at this point. ⏎  ⏎ I recommend an epidemiological study ⏎ at Fallcreek Academic Hospital ⏎ to identify the viral agent.
旧: 男性受害者，22岁，Rh阴性O型血。 ⏎ 死因：受害者在被未知武器切割和 ⏎ 抓伤后失血过多而死… ⏎  ⏎ 备注：尸体体内含有未知黑色物质的残留， ⏎ 主要集中在肺部和生殖器区域。 ⏎  ⏎ 肺部绝对是第一个接触到该物质（看起来具 ⏎ 有寄生性）的区域， ⏎ 这很可能是通过呼吸系统吸入了某种毒品后导致的。 ⏎  ⏎ 此死因可能与受害者女友的死亡存在关联。 ⏎ 与受害者不同，该女的肺部非常干净， ⏎ 但她的生殖器官里却发现了这种物质。 ⏎ 目前来看，通过生殖接触以及 ⏎ 身体任何粘膜接触（例如性行为） ⏎ 进行传染的可能性极高。 ⏎  ⏎ 我建议在秋溪大学附属医院展开流行病学研究， ⏎ 以查明这种病毒病原体。
新: 男性受害者，22岁，Rh阴性O型血。 ⏎ 死因：受害者在被未知武器切割和 ⏎ 抓伤后失血过多而死… ⏎  ⏎ 备注：尸体体内含有未知黑色物质的残留， ⏎ 主要集中在肺部和生殖器区域。 ⏎  ⏎ 肺部绝对是第一个接触到该物质（看起来 ⏎ 具有寄生性）的区域， ⏎ 这很可能是通过呼吸系统吸入了某种毒品后导致的。 ⏎  ⏎ 此死因可能与受害者女友的死亡存在关联。 ⏎ 与受害者不同，该女的肺部非常干净， ⏎ 但她的生殖器官里却发现了这种物质。 ⏎ 目前来看，通过生殖接触以及 ⏎ 身体任何粘膜接触（例如性行为） ⏎ 进行传染的可能性极高。 ⏎  ⏎ 我建议在秋溪大学附属医院展开流行病学研究， ⏎ 以查明这种病毒病原体。
  换行点7 拆词(具有) -> 移位 k=1 …物质（看起来 ⇄ 具有寄生性）…
```
### idx=1422 key=453005324
```
EN: The flower is sensitive to light. Nevertheless ⏎ it has a very effective defense system: ⏎ if exposed to a source of light it closes ⏎ its petals hermetically, protecting ⏎ it's photosensitive cells. ⏎  ⏎ Sunlight was unable to prevent ⏎ its propagation throughout Fallcreek County. ⏎ The flowers feed and propagate from ⏎ a supremely widespread root system which ⏎ - in order to destroy it - must be terminated ⏎ at the source. ⏎  ⏎ Regrettably, because of the complex ⏎ root structure, we are unable to locate ⏎ it's origins at this time.
旧: 这种花对光线很敏感。然而它有一套非 ⏎ 常有效的防御系统： ⏎ 一旦暴露在光源下，它就会紧紧闭合花瓣， ⏎ 以保护其感光细胞。 ⏎  ⏎ 阳光也无法阻止它在整个秋溪县的蔓延繁殖。 ⏎ 这些花是通过一个极度庞大的根系网络 ⏎ 获取养分并扩散的， ⏎ 要彻底铲除它们，必须从源头上斩断根系。 ⏎  ⏎ 遗憾的是，由于其复杂的根系结构， ⏎ 我们目前仍然无法找到它的源头所在。
新: 这种花对光线很敏感。然而它有一套 ⏎ 非常有效的防御系统： ⏎ 一旦暴露在光源下，它就会紧紧闭合花瓣， ⏎ 以保护其感光细胞。 ⏎  ⏎ 阳光也无法阻止它在整个秋溪县的蔓延繁殖。 ⏎ 这些花是通过一个极度庞大的根系网络 ⏎ 获取养分并扩散的， ⏎ 要彻底铲除它们，必须从源头上斩断根系。 ⏎  ⏎ 遗憾的是，由于其复杂的根系结构， ⏎ 我们目前仍然无法找到它的源头所在。
  换行点0 拆词(非常) -> 移位 k=1 …然而它有一套 ⇄ 非常有效的防…
```
### idx=1424 key=503336972
```
EN: "Mens sana in corpore sano." ⏎  ⏎ Because the spirit is also influenced by the body, ⏎ Delta Theta Gamma requires that its members ⏎ be in excellent physical condition. ⏎  ⏎ On Wednesday, the traditional rowing ⏎ and nature orientation trials will take place. ⏎ To obtain instructions, meet at the summer ⏎ headquarters of the fraternity on the edge of the lake!
旧: “健全的精神寓于健康的体魄。” ⏎  ⏎ 因为人的精神同样受到肉体的影响， ⏎ 德尔塔·西塔·伽马兄弟会要求其成员必须具备极 ⏎ 其优秀的身体素质。 ⏎  ⏎ 本周三将进行传统的赛艇和户外定向越野测验。 ⏎ 请到湖畔的兄弟会避暑总部集合获取指示！
新: “健全的精神寓于健康的体魄。” ⏎  ⏎ 因为人的精神同样受到肉体的影响， ⏎ 德尔塔·西塔·伽马兄弟会要求其成员必须具备 ⏎ 极其优秀的身体素质。 ⏎  ⏎ 本周三将进行传统的赛艇和户外定向越野测验。 ⏎ 请到湖畔的兄弟会避暑总部集合获取指示！
  换行点3 拆词(极其) -> 移位 k=1 …成员必须具备 ⇄ 极其优秀的身…
```
### idx=1429 key=637554700
```
EN: May 6, 1904. 103rd Traditional Ceremony ⏎ of the Assembly of Lodges; Paris, in the ⏎ basement of 51 rue de Montmorency.  ⏎  ⏎ We thank each Head Lodge of our ninety-six ⏎ brother countries to have sent their Master ⏎ of Ceremonies on this occasion.  ⏎  ⏎ On the occasion of this celebration, ⏎ the High Brothers have unanimously ⏎ voted to enscribe the recent works ⏎ of Leonard and Herbert Friedman ⏎ in the Fraternity's codices.  ⏎  ⏎ Their discoveries concerning the possibility ⏎ of eternal life promise Delta Theta Gamma ⏎ a paramount place among the prominent powers ⏎ of this planet. ⏎ 
旧: 1904年5月6日。 ⏎ 第103届传统集会仪式在巴黎蒙莫朗西街 ⏎ 51号的地下室举行。 ⏎  ⏎ 在此我们感谢来自96个友好国家的各分会 ⏎ 派出了他们的代表。 ⏎  ⏎ 在此次庆典上，高阶兄弟们一致投票通过， ⏎ 将莱纳德和赫伯特·弗里德曼最近的科学成 ⏎ 果载入兄弟会法典。 ⏎  ⏎ 他们关于永生可能的发现， ⏎ 将许诺德尔塔·西塔·伽马在地球的 ⏎ 各大顶峰势力中占据至高无上的地位。 ⏎ 
新: 1904年5月6日。 ⏎ 第103届传统集会仪式在巴黎蒙莫朗西街 ⏎ 51号的地下室举行。 ⏎  ⏎ 在此我们感谢来自96个友好国家的各分会 ⏎ 派出了他们的代表。 ⏎  ⏎ 在此次庆典上，高阶兄弟们一致投票通过， ⏎ 将莱纳德和赫伯特·弗里德曼最近的科学 ⏎ 成果载入兄弟会法典。 ⏎  ⏎ 他们关于永生可能的发现， ⏎ 将许诺德尔塔·西塔·伽马在地球的 ⏎ 各大顶峰势力中占据至高无上的地位。 ⏎ 
  换行点8 拆词(成果) -> 移位 k=1 …曼最近的科学 ⇄ 成果载入兄弟…
```
### idx=1441 key=256
```
EN: You are starting the story in "1 player" mode. ⏎  ⏎ At any time, a second player can join you and take control ⏎ of your teammate by pressing the ENTER key.
旧: 你将以“单人”模式开始故事。 ⏎  ⏎ 第二名玩家随时可以按回车键加入游 ⏎ 戏，并接管你的队友。
新: 你将以“单人”模式开始故事。 ⏎  ⏎ 第二名玩家随时可以按回车键加入 ⏎ 游戏，并接管你的队友。
  换行点2 拆词(游戏) -> 移位 k=1 …按回车键加入 ⇄ 游戏，并接管…
```
### idx=1533 key=117489676
```
EN: There has to be some kind of logic to this thing. We must ⏎ be missing a bit otherwise I would have seen the combination! 
旧: 这玩意儿的设计肯定有一定的逻辑。 ⏎ 我们绝对是漏掉了什么，否则我早就看 ⏎ 出它的密码组合了！
新: 这玩意儿的设计肯定有一定的逻辑。 ⏎ 我们绝对是漏掉了什么，否则我早就 ⏎ 看出它的密码组合了！
  换行点1 拆词(看出) -> 移位 k=1 …，否则我早就 ⇄ 看出它的密码…
```
### idx=1929 key=50369300
```
EN: Sven... Sven... Don't leave me... ⏎ You have to stay with me!
旧: 斯文…斯文…不要丢下我…你一定要撑 ⏎ 住！我们要在一起！
新: 斯文…斯文…不要丢下我…你一定要 ⏎ 撑住！我们要在一起！
  换行点0 拆词(撑住) -> 移位 k=1 …我…你一定要 ⇄ 撑住！我们要…
```
### idx=2298 key=1967132696
```
EN: Corey is too weak to get out alone. He needs us!
旧: 科里现在太虚弱了，根本没办法自己逃 ⏎ 出来。他需要我们！
新: 科里现在太虚弱了，根本没办法自己 ⏎ 逃出来。他需要我们！
  换行点0 拆词(逃出来) -> 移位 k=1 …本没办法自己 ⇄ 逃出来。他需…
```
### idx=2299 key=8388609
```
EN: Corey is too weak to get out alone. He needs us!
旧: 科里现在太虚弱了，根本没办法自己逃 ⏎ 出来。他需要我们！
新: 科里现在太虚弱了，根本没办法自己 ⏎ 逃出来。他需要我们！
  换行点0 拆词(逃出来) -> 移位 k=1 …本没办法自己 ⇄ 逃出来。他需…
```
### idx=2322 key=50380824
```
EN: I don't want to die in bed... not like this anyway.
旧: 我可不想在病床上等死…至少绝对不 ⏎ 想以这种方式死掉。
新: 我可不想在病床上等死…至少绝对 ⏎ 不想以这种方式死掉。
  换行点0 拆词(不想) -> 移位 k=1 …死…至少绝对 ⇄ 不想以这种方…
```
### idx=2520 key=8388610
```
EN: "Here lies Corey Wilde, who lived in anger and died ⏎ because of it". Who wrote this crap? Huh? Who??
旧: “这里躺着科里·怀尔德，他在 ⏎ 愤怒中度过余生，并因此而死。” ⏎ 到底是哪个王八蛋写了这些垃圾玩 ⏎ 意？啊？到底是谁？？
新: “这里躺着科里·怀尔德，他在 ⏎ 愤怒中度过余生，并因此而死。” ⏎ 到底是哪个王八蛋写了这些垃圾 ⏎ 玩意？啊？到底是谁？？
  换行点2 拆词(玩意) -> 移位 k=1 …写了这些垃圾 ⇄ 玩意？啊？到…
```
### idx=2783 key=364933417
```
EN: "The Balance of the Elements"... A fitness book, perhaps.
旧: 《元素的平衡》 ⏎ …大概是一本强身健体的健身书吧。
新: 《元素的平衡》… ⏎ 大概是一本强身健体的健身书吧。
  换行点0 行首标点(…) -> 移位 k=-1 …素的平衡》… ⇄ 大概是一本强…
```
### idx=3775 key=151023724
```
EN: ...The new illness is spreading quickly, ⏎ particularly through unprotected ⏎ sexual relations. ⏎  ⏎ From nine patients last month, ⏎ we have reached thirty-four this ⏎ month. All victims are young ⏎ Fallcreek students...
旧: …这种新疾病传播迅速，尤其是通过无保护的性接触。 ⏎  ⏎ 上个月还是九名患者，这个月我们已 ⏎ 经达到了三十四名。 ⏎ 所有受害者都是秋溪学校的年轻学生…
新: …这种新疾病传播迅速，尤其是通过无保护的性接触。 ⏎  ⏎ 上个月还是九名患者，这个月我们 ⏎ 已经达到了三十四名。 ⏎ 所有受害者都是秋溪学校的年轻学生…
  换行点2 拆词(已经) -> 移位 k=1 …，这个月我们 ⇄ 已经达到了三…
```
### idx=3782 key=268464236
```
EN: (You find an old page ⏎ stuck inside a diary) ⏎  ⏎ " ...Herbert and I have succeeded in ⏎ creating a stable solution which slows ⏎ down the aging process in cells. ⏎ However, the mortifia dosages are not ⏎ yet perfect due to the number ⏎ of secondary effects. ⏎  ⏎ We need to experiment more. ⏎ Experiment a lot. ⏎  ⏎ It's difficult to find human guinea pigs ⏎ in excellent physical health, but ⏎ fortunately the fraternity is helping us... "
旧: （你在一本硬皮日记里发现了一张泛黄的旧纸页） ⏎  ⏎ “…赫伯特和我已成功创造了一种 ⏎ 能延缓细胞衰老过程的稳定溶液。 ⏎ 然而，由于大量的副作用， ⏎ 死亡之花的剂量尚不完美。 ⏎  ⏎ 我们需要进行更多的实验。 ⏎ 进行大量的实验。 ⏎  ⏎ 虽然很难找到身体状况极佳的人类小白鼠， ⏎ 但幸运的是，兄弟会正在为我们提供源 ⏎ 源不断的实验体…”
新: （你在一本硬皮日记里发现了一张泛黄的旧纸页） ⏎  ⏎ “…赫伯特和我已成功创造了一种 ⏎ 能延缓细胞衰老过程的稳定溶液。 ⏎ 然而，由于大量的副作用， ⏎ 死亡之花的剂量尚不完美。 ⏎  ⏎ 我们需要进行更多的实验。 ⏎ 进行大量的实验。 ⏎  ⏎ 虽然很难找到身体状况极佳的人类小白鼠， ⏎ 但幸运的是，兄弟会正在为我们提供 ⏎ 源源不断的实验体…”
  换行点11 拆词(源源不断) -> 移位 k=1 …在为我们提供 ⇄ 源源不断的实…
```
### idx=3794 key=469790828
```
EN: May 6, 1904. 103rd Traditional Ceremony ⏎ of the Assembly of Lodges; Paris, in the ⏎ basement of 51 rue de Montmorency.  ⏎  ⏎ We thank each Head Lodge of our ninety-six ⏎ brother countries to have sent their Master ⏎ of Ceremonies on this occasion.  ⏎  ⏎ On the occasion of this celebration, ⏎ the High Brothers have unanimously ⏎ voted to enscribe the recent works ⏎ of Leonard and Herbert Friedman ⏎ in the Fraternity's codices.  ⏎  ⏎ Their discoveries concerning the possibility ⏎ of eternal life promise Delta Theta Gamma ⏎ a paramount place among the prominent ⏎ powers of this planet.
旧: 1904年5月6日。 ⏎ 第103届传统集会仪式在巴黎蒙莫朗西街 ⏎ 51号的地下室举行。 ⏎  ⏎ 在此我们感谢来自96个友好国家的各分会 ⏎ 派出了他们的代表。 ⏎  ⏎ 在此次庆典上，高阶兄弟们一致投票通过， ⏎ 将莱纳德和赫伯特·弗里德曼最近的科学成 ⏎ 果载入兄弟会法典。 ⏎  ⏎ 他们关于永生可能的发现， ⏎ 将许诺德尔塔·西塔·伽马在地球的 ⏎ 各大顶峰势力中占据至高无上的地位。 ⏎ 
新: 1904年5月6日。 ⏎ 第103届传统集会仪式在巴黎蒙莫朗西街 ⏎ 51号的地下室举行。 ⏎  ⏎ 在此我们感谢来自96个友好国家的各分会 ⏎ 派出了他们的代表。 ⏎  ⏎ 在此次庆典上，高阶兄弟们一致投票通过， ⏎ 将莱纳德和赫伯特·弗里德曼最近的科学 ⏎ 成果载入兄弟会法典。 ⏎  ⏎ 他们关于永生可能的发现， ⏎ 将许诺德尔塔·西塔·伽马在地球的 ⏎ 各大顶峰势力中占据至高无上的地位。 ⏎ 
  换行点8 拆词(成果) -> 移位 k=1 …曼最近的科学 ⇄ 成果载入兄弟…
```
### idx=3835 key=469790856
```
EN: We would like to inform students that ⏎ we have apprehended the stalker who was ⏎ stealing panties from unlocked rooms ⏎ in the Dormitory. He has been identified ⏎ as Mr. Ward, Sociology Professor. ⏎ The pervert was trapped using expensive ⏎ underwear as bait - our thanks to all the sisters ⏎ on campus who made this possible. 
旧: 各位同学请注意： ⏎ 日前，我们已成功抓获在宿舍区流窜的“内衣大盗”。 ⏎ 此人此前专门潜入未锁门的房间盗窃内衣裤。 ⏎ 经查明，该变态狂竟是我们的社会学 ⏎ 教授——沃德先生。 ⏎ 为了诱捕这个死变态，我们特意使 ⏎ 用了高档内衣作为诱饵。 ⏎ 在此，特别感谢全校所有为此付出努 ⏎ 力的姐妹会成员们！
新: 各位同学请注意： ⏎ 日前，我们已成功抓获在宿舍区流窜的“内衣大盗”。 ⏎ 此人此前专门潜入未锁门的房间盗窃内衣裤。 ⏎ 经查明，该变态狂竟是我们的社会学 ⏎ 教授——沃德先生。 ⏎ 为了诱捕这个死变态，我们特意 ⏎ 使用了高档内衣作为诱饵。 ⏎ 在此，特别感谢全校所有为此付出 ⏎ 努力的姐妹会成员们！
  换行点5 拆词(使用) -> 移位 k=1 …态，我们特意 ⇄ 使用了高档内…
  换行点7 拆词(努力) -> 移位 k=1 …所有为此付出 ⇄ 努力的姐妹会…
```
### idx=3836 key=486568072
```
EN: New 'Wind Blows 2007' will improve ⏎ the abilities of your PC! To use its ⏎ full potential, 'Wind Blows 2007' ⏎ deletes 99,9 percent of all viruses found, ⏎ downloads pirate music to your personal taste, ⏎ generates insults for discussions and chat rooms, ⏎ cracks passwords to the best dating sites! ⏎ This version includes all-new humorous ⏎ error messages!
旧: 全新“Wind Blows 2007”将提升您的电脑性能！ ⏎ 为了充分释放其潜力，“Wind Blows 2007”可删 ⏎ 除99.9%的已知病毒， ⏎ 根据您的个人喜好下载盗版音乐， ⏎ 在论坛和聊天室里自动生成骂人的话， ⏎ 甚至能破解最佳交友网站的密码！ ⏎ 本版本包含全新的幽默错误提示信息！
新: 全新“Wind Blows 2007”将提升您的电脑性能！ ⏎ 为了充分释放其潜力，“Wind Blows 2007”可 ⏎ 删除99.9%的已知病毒， ⏎ 根据您的个人喜好下载盗版音乐， ⏎ 在论坛和聊天室里自动生成骂人的话， ⏎ 甚至能破解最佳交友网站的密码！ ⏎ 本版本包含全新的幽默错误提示信息！
  换行点1 拆词(删除) -> 移位 k=1 …2007”可 ⇄ 删除99.9…
```
### idx=3840 key=553676936
```
EN: Donnie Draco's unfinished letter ⏎  ⏎ That's it! I'm an official Frat brother ⏎ of Delta Thêta Gamma ! Fallcreek is teeming ⏎ with pretty girls! Wine, women and music ⏎ are a way of life around here! ⏎  ⏎ Lately though it seems like a new STD ⏎ has invaded the campus. It gives you ⏎ black spots on your genitals... ⏎  ⏎ Yeah man, everybody's sleeping around ⏎ with anybody, without any protection. ⏎ Seriously dude, we can't get drunk enough. ⏎ Anyway, I wonder if what I got down there ⏎ is a beauty mark...  or something else.[...]
旧: 唐尼·德拉科未寄出的信： ⏎  ⏎ 就这样！我正 ⏎ 式成为德尔塔·西塔·伽马兄弟会的成员了！ ⏎ 秋溪到处都是漂亮姑娘！ ⏎ 美酒、女人和音乐就是这里的生活方式！ ⏎  ⏎ 不过最近，一种新的性传播疾病似乎席卷了校园。 ⏎ 它会在你的生殖器上留下黑斑… ⏎  ⏎ 是啊老兄，每个人都在没有任何保护措施的情 ⏎ 况下跟任何人乱搞。 ⏎ 说真的哥们，我们再怎么喝都不嫌多。 ⏎ 总之，我怀疑我下面长出来的那个东西 ⏎ 是颗美人痣…还是别的什么。[...]
新: 唐尼·德拉科未寄出的信： ⏎  ⏎ 就这样！我 ⏎ 正式成为德尔塔·西塔·伽马兄弟会的成员了！ ⏎ 秋溪到处都是漂亮姑娘！ ⏎ 美酒、女人和音乐就是这里的生活方式！ ⏎  ⏎ 不过最近，一种新的性传播疾病似乎席卷了校园。 ⏎ 它会在你的生殖器上留下黑斑… ⏎  ⏎ 是啊老兄，每个人都在没有任何保护措施的 ⏎ 情况下跟任何人乱搞。 ⏎ 说真的哥们，我们再怎么喝都不嫌多。 ⏎ 总之，我怀疑我下面长出来的那个东西 ⏎ 是颗美人痣…还是别的什么。[...]
  换行点2 拆词(正式) -> 移位 k=1 …就这样！我 ⇄ 正式成为德尔…
  换行点10 拆词(情况) -> 移位 k=1 …何保护措施的 ⇄ 情况下跟任何…
```

## 已排除（人工核实后不改, 附理由）

### idx=564 key=3472909060 违规={0: '拆词(上存)'}
- 理由: jieba 误合：“服务器上|存了”被切成 token“上存”（词典词，此语境不适用），自然断行
```
EN: Some slightly idiotic interns stored a recipe ⏎ for home-made dynamite on the server.
ZH: 一些有点蠢的实习生在服务器上 ⏎ 存了自制炸药的配方。
```
### idx=1067 key=121643016 违规={0: '拆词(中未)'}
- 理由: jieba 误合：“）中|未发现”被切成 token“中未”（法律文本词，此语境不适用），自然断行
```
EN: No Obscure 2 save data present on ⏎ memory card (8MB) (for PlayStation®2) ⏎ in MEMORY CARD slot 1.
ZH: 插槽1的记忆卡（8MB）（for PlayStation®2）中 ⏎ 未发现《恶夜杀机2》的保存数据。
```
### idx=1068 key=138420232 违规={0: '拆词(中未)'}
- 理由: jieba 误合：同 1067
```
EN: No Obscure 2 save data present on ⏎ memory card (8MB) (for PlayStation®2) ⏎ in MEMORY CARD slot 2.
ZH: 插槽2的记忆卡（8MB）（for PlayStation®2）中 ⏎ 未发现《恶夜杀机2》的保存数据。
```
### idx=2019 key=3 违规={0: '行首标点(…)'}
- 理由: 英文原文第 2 行本身以 "..." 开头（The ceiling has collapsed... / ...someone could have been underneath...），中文如实对应，不做改动
```
EN: The ceiling has collapsed... ⏎ ...someone could have been underneath...
ZH: 天花板塌落下来了… ⏎ …要是当时有人在底下，那可就惨了…
```
### idx=3757 key=16805988 违规={0: '拆词(aaaaaaaaaaaaaaaaaaaaa)', 1: '拆词(aaaaaaaaaaaaaaaaa)', 2: '拆词(aaaaaaaaaaaaaaaaaaaaaa)', 3: '拆词(aaaaaaaaaaaaaaaaaaaaaa)', 4: '拆词(aaaaaaaaaaaaaaaaa)', 5: '拆词(aaaaaaaaaaaaaaaaaaaaaa)', 6: '拆词(aaaaaaaaaaaaaaaaaaaaaaaaaa)', 7: '拆词(aaaaaaaaaaaaaaaaaaaa)', 8: '拆词(aaaaaaaaaaaaaaaaaaaaaa)', 9: '拆词(aaaaaaaaaaaaaaa)', 10: '拆词(aaaaaaaaaaaaa)'}
- 理由: 调试占位文本（en 与 zh 均为 aaaa 串，无实际显示内容）
```
EN: aaaaaaaaaaaaaa ⏎ aaaaaaa ⏎ aaaaaaaaaa ⏎ aaaaaaaaaaaa ⏎ aaaaaaaaaa ⏎ aaaaaaa ⏎ aaaaaaaaaaaaaaa ⏎ aaaaaaaaaaa ⏎ aaaaaaaaa ⏎ aaaaaaaaaaaaa ⏎ aa ⏎ aaaaaaaaaaa
ZH: aaaaaaaaaaaaaa ⏎ aaaaaaa ⏎ aaaaaaaaaa ⏎ aaaaaaaaaaaa ⏎ aaaaaaaaaa ⏎ aaaaaaa ⏎ aaaaaaaaaaaaaaa ⏎ aaaaaaaaaaa ⏎ aaaaaaaaa ⏎ aaaaaaaaaaaaa ⏎ aa ⏎ aaaaaaaaaaa
```
### idx=3780 key=234909804 违规={6: '拆词(动植物)'}
- 理由: jieba 误合：“还在动|植物”被切成 token“动植物”；动属上句“还在动”，自然断行
```
EN: (Written in a wild ⏎ infantile handwriting) ⏎  ⏎  ⏎ Mummy dead ⏎ House is all Jedidiah's ⏎ Jedidiah sad ⏎ Papa still moving ⏎ Plants good for daddy...
ZH: （用歪歪扭扭的幼稚字体写着） ⏎  ⏎  ⏎ 妈妈死了 ⏎ 房子全是杰迪戴亚的了 ⏎ 杰迪戴亚伤心 ⏎ 爸爸还在动 ⏎ 植物对爸爸好…
```
