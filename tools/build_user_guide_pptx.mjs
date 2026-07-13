import fs from "node:fs/promises";
import path from "node:path";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const output = process.argv[2];
const qa = process.argv[3];
const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const C={ink:"#17212B",muted:"#65727E",soft:"#F4F7F9",panel:"#EAF0F4",rule:"#C6D0D8",accent:"#63C7E8",blue:"#2F7CF6",green:"#2E9D72",gold:"#B97917",red:"#C24B4B",white:"#FFFFFF"};

function shape(slide,geometry,position,fill="none",line="none",width=0){return slide.shapes.add({geometry,position,fill,line:{style:"solid",fill:line,width}})}
function text(slide,value,left,top,width,height,size=22,bold=false,color=C.ink,align="left"){
  const box=shape(slide,"textbox",{left,top,width,height});
  box.text=value;
  box.text.style={fontFamily:"Microsoft YaHei",fontSize:size,bold,color,alignment:align,verticalAlignment:"middle"};
  return box;
}
function title(slide,value,kicker="INKTRACE · 小白写手指南"){
  text(slide,kicker,50,28,650,26,14,true,C.muted);
  text(slide,value,50,64,1160,68,39,true,C.ink);
  shape(slide,"rect",{left:50,top:148,width:1180,height:2},C.rule);
}
function footer(slide,n){text(slide,String(n).padStart(2,"0"),1165,670,65,22,13,true,C.muted,"right")}
function note(slide,value,top=568,color=C.blue){
  shape(slide,"rect",{left:50,top,width:1180,height:70},C.soft,color,2);
  text(slide,value,74,top+10,1132,50,21,true,C.ink,"center");
}
function bullets(slide,items,{left=72,top=182,width=1110,size=22,gap=68,color=C.blue}={}){
  items.forEach((item,i)=>{
    shape(slide,"ellipse",{left,top:top+i*gap+17,width:11,height:11},i===0?color:C.accent);
    text(slide,item,left+28,top+i*gap,width-28,52,size,false,C.ink);
  });
}
function panel(slide,heading,body,left,top,width,height,accent=C.blue){
  shape(slide,"rect",{left,top,width,height},C.soft,C.rule,1);
  shape(slide,"rect",{left,top,width:7,height},accent);
  text(slide,heading,left+24,top+14,width-42,36,22,true,C.ink);
  text(slide,body,left+24,top+58,width-42,height-72,18,false,C.muted);
}
function twoCol(slide,leftTitle,leftItems,rightTitle,rightItems,{leftAccent=C.blue,rightAccent=C.green,noteText=""}={}){
  panel(slide,leftTitle,leftItems.join("\n"),50,190,565,320,leftAccent);
  panel(slide,rightTitle,rightItems.join("\n"),635,190,595,320,rightAccent);
  if(noteText) note(slide,noteText,548);
}
function steps(slide,items,{top=225,accent=C.blue}={}){
  const gap=18; const width=(1180-gap*(items.length-1))/items.length;
  items.forEach((item,i)=>{
    const left=50+i*(width+gap);
    shape(slide,"rect",{left,top,width,height:220},i===items.length-1?"#DCEAFF":C.soft,C.rule,1);
    text(slide,String(i+1).padStart(2,"0"),left+18,top+18,70,48,31,true,i===items.length-1?accent:C.muted);
    text(slide,item,left+18,top+82,width-36,112,21,true,C.ink);
  });
}
function addBulletsSlide(head,items,noteText="",opts={}){
  const s=deck.slides.add(); s.background.fill=C.white; title(s,head); bullets(s,items,opts); if(noteText)note(s,noteText); footer(s,deck.slides.items.length);
}
function addTwoColSlide(head,leftTitle,leftItems,rightTitle,rightItems,noteText="",opts={}){
  const s=deck.slides.add(); s.background.fill=C.white; title(s,head); twoCol(s,leftTitle,leftItems,rightTitle,rightItems,{...opts,noteText}); footer(s,deck.slides.items.length);
}

// 01 封面
{
  const s=deck.slides.add(); s.background.fill=C.white;
  text(s,"INKTRACE V2.0",50,42,340,28,15,true,C.muted);
  text(s,"小白写手\n完整操作指南",50,155,820,180,64,true,C.ink);
  text(s,"从第一次配置，到安全采用每一份候选新稿",50,370,940,46,27,false,C.muted);
  shape(s,"rect",{left:50,top:515,width:1180,height:104},C.soft,C.accent,2);
  text(s,"你始终是作者。AI 只准备候选方案，正文、方向、计划和故事记忆都由你确认。",78,535,1124,64,23,true,C.ink,"center");
  footer(s,1);
}

// 02
addBulletsSlide("先用一句话理解 InkTrace",[
  "你负责决定故事；InkTrace 负责整理资料和准备候选方案。",
  "AI 写完以后先进入候选稿区，不会直接修改正式正文。",
  "方向、计划、候选稿和故事记忆，需要分别确认。",
  "预算、分析和风格数据只帮助判断，不替你评价作品。",
  "遇到阻断冲突或费用不明时，系统会先停下等你处理。"
],"只要记住“先看、再改、再确认”，就不会把 AI 建议误当成正式正文。",{gap:70});

// 03
{
  const s=deck.slides.add(); s.background.fill=C.white; title(s,"六条安全底线，任何时候都不变");
  panel(s,"候选稿隔离","AI 结果先保存在候选区。",50,190,360,135,C.blue);
  panel(s,"作者亲自采用","接受和应用都要你点击。",430,190,380,135,C.green);
  panel(s,"继续不等于采用","继续下一章不会采用当前稿。",830,190,400,135,C.gold);
  panel(s,"四道确认分开","方向、计划、正文、记忆各自确认。",50,345,360,135,C.blue);
  panel(s,"未知就先停","预算和用量不明时保护性暂停。",430,345,380,135,C.red);
  panel(s,"关闭不删数据","关闭助手不会删除正文和资料。",830,345,400,135,C.green);
  note(s,"如果你不确定某个按钮会做什么，先不要点“应用”或“放弃”，先看说明。",540,C.gold); footer(s,3);
}

// 04
addTwoColSlide("先认识四个最常见的词","正文与候选",[
  "正式正文：你真正保存的小说内容",
  "候选稿：AI 准备、等待你审阅的新稿",
  "候选版本：同一候选稿的 v1、v2 等版本"
],"资料与上下文",[
  "写作资料：大纲、人物、时间线、伏笔",
  "写作上下文：为当前任务整理的必要资料",
  "故事记忆：保持长篇连续性的正式资料"
],"候选稿生成成功，只表示“有一份稿可以看”，不表示正文已经改变。");

// 05
{
  const s=deck.slides.add(); s.background.fill=C.white; title(s,"第一次使用，按五步完成准备");
  steps(s,["创建或\n导入作品","配置模型\n并测试连接","打开需要的\n写作助手","设置费用\n与预算保护","只生成一章\n完成试跑"]); note(s,"第一次不要直接运行很多章；先确认创建、保存、候选稿和采用流程都正常。",520); footer(s,5);
}

// 06
addTwoColSlide("新建和导入后，都要先检查作品","新建空白作品",[
  "在书架选择新建作品",
  "填写作品名并创建第一章",
  "先写一小段并确认保存成功"
],"导入已有 TXT",[
  "导入前备份原文件并整理章节标题",
  "导入后抽查第一章、中间章和最后一章",
  "检查乱码、漏章、顺序和章节标题"
],"拆章或乱码有问题时先修复，不要马上启动初始化分析。");

// 07
addBulletsSlide("模型配置只需按顺序完成",[
  "进入“设置中心 → AI 设置”，添加或选择模型服务。",
  "填写默认模型、服务密钥，以及服务要求的地址。",
  "点击“测试连接”；成功后再配置任务模型。",
  "为分析、规划、写作、审阅和重写任务选择模型。",
  "确认分析和写作任务可用，最后保存 AI 配置。",
  "失败时检查密钥、模型名称、地址、账户权限和网络。"
],"模型密钥只填在设置页；不要放进正文、人物资料或问题截图。",{top:170,gap:62,size:21});

// 08
addTwoColSlide("写作助手可以在设置中心直接开关","新手先打开",[
  "接着写、选区改写",
  "大纲辅助、引用来源",
  "AI 用量与预算、创作分析"
],"熟悉后再打开",[
  "多章续写、自动续写",
  "@引用、风格画像",
  "开篇助手"
],"开关只控制是否使用这个助手，不会绕过任何确认门，也不会删除历史数据。");

// 09
{
  const s=deck.slides.add(); s.background.fill=C.white; title(s,"写作台按“章节—正文—辅助”理解");
  panel(s,"左侧 · 章节","选择、新建、重命名和调整章节。启动 AI 前先确认选对章节。",50,205,330,290,C.blue);
  panel(s,"中间 · 正式正文","你真正保存的小说内容。观察“保存中、已保存、离线、冲突”等状态。",400,205,480,290,C.green);
  panel(s,"右侧 · 资料与审阅","管理大纲、人物、时间线、伏笔；使用 AI；集中处理候选稿和冲突。",900,205,330,290,C.gold);
  note(s,"切换右侧工具前，如提示有未保存修改，先保存或明确放弃。",545); footer(s,9);
}

// 10
addTwoColSlide("保存状态决定你下一步该做什么","可以继续",[
  "已保存：可以切章或关闭",
  "保存中：等待几秒",
  "当前离线：保留页面，恢复网络后确认"
],"必须处理",[
  "保存失败：按提示重试",
  "版本冲突：选择本地或服务器版本",
  "不确定时先复制本地重要内容"
],"不要靠反复刷新“解决冲突”；本地和服务器版本必须由作者明确选择。",{rightAccent:C.red});

// 11
addBulletsSlide("已有多章正文时，先做初始化分析",[
  "打开作品和有效章节，进入右侧“AI”。",
  "确认使用前检查显示模型配置已完成。",
  "在“初始化分析”点击“启动初始化”。",
  "观察分析成功、空章节和失败章节数量。",
  "任务可以暂停、继续、取消；失败后可按提示重试。",
  "空章节不是程序故障，失败章节才需要进一步检查。"
],"初始化只整理作品信息，不会生成或修改正式正文。",{top:170,gap:62,size:21});

// 12
addTwoColSlide("续写前，先构建当前章节的写作上下文","显示可继续",[
  "前文和资料已整理",
  "可以进入方向与计划",
  "仍要检查资料是否符合你的实际意图"
],"受限或无法继续",[
  "补选章节、正文、大纲或人物资料",
  "确认计划，或处理预算和阻断冲突",
  "处理后重新构建上下文"
],"写作上下文是本次任务的资料包，不是把整本书原样塞给 AI。",{rightAccent:C.red});

// 13
{
  const s=deck.slides.add(); s.background.fill=C.white; title(s,"一章候选稿的完整流程，有四次作者决定");
  const labels=["构建上下文","选择故事方向","确认章节计划","生成候选稿","审阅并接受","应用到章节草稿"];
  const width=180,gap=17,top=250;
  labels.forEach((v,i)=>{const left=50+i*(width+gap); shape(s,"rect",{left,top,width,height:112},i===5?"#DCEAFF":C.soft,C.rule,1); text(s,v,left+12,top+20,width-24,72,19,true,C.ink,"center"); if(i<labels.length-1) text(s,"→",left+width,top+31,gap,50,25,true,C.blue,"center")});
  text(s,"作者决定",248,390,160,34,18,true,C.blue,"center");
  text(s,"作者决定",445,390,160,34,18,true,C.blue,"center");
  text(s,"作者决定",839,390,160,34,18,true,C.blue,"center");
  text(s,"作者决定",1036,390,160,34,18,true,C.blue,"center");
  note(s,"确认计划不等于接受文字；接受候选稿也不等于已经保存正文。",540,C.gold); footer(s,13);
}

// 14
addBulletsSlide("选择故事方向时，先看它是否适合你的故事",[
  "点击“生成方向”，阅读每个方向的标签和剧情摘要。",
  "优先选择能推进本章主要目标的方向。",
  "检查人物有没有突然改变，核心秘密有没有提前揭开。",
  "确认它能自然接上上一章，并且一章内能够推进。",
  "由你点击“选择方向”；系统不能替你选择。"
],"最热闹的方向不一定最好，最适合当前故事阶段的方向才有用。",{gap:72});

// 15
addTwoColSlide("章节计划要说清楚“做什么”和“不做什么”","确认前检查",[
  "本章主要目标和结尾变化",
  "必须出现的人物、事件或伏笔",
  "暂时禁止发生的事情"
],"你的操作",[
  "满意：点击确认计划",
  "不满意：拒绝计划并重新准备",
  "再查看写作任务，确认可执行"
],"确认计划只允许系统按计划准备候选稿，不代表你接受最后写出的文字。");

// 16
addBulletsSlide("生成候选稿前，再看一眼写作任务",[
  "点击“查看任务详情”，核对目标、必须包含和禁止事项。",
  "任务状态可执行且内容正确时，点击“确认可执行”。",
  "在“续写与候选稿”点击“生成候选稿”。",
  "等待候选稿出现在列表中；正式正文此时不会改变。",
  "执行中可以暂停、继续或取消；失败后先看原因再重试。"
],"候选稿生成成功 = 有一份稿可以看；不等于已经写进你的章节。",{gap:72});

// 17
{
  const s=deck.slides.add(); s.background.fill=C.white; title(s,"候选稿至少检查六件事");
  panel(s,"人物","性格、动机、关系和称呼是否一致",50,190,370,125,C.blue);
  panel(s,"时间","先后、日期、昼夜和人物位置是否合理",440,190,370,125,C.green);
  panel(s,"设定","地点、世界规则、物品和能力是否冲突",830,190,400,125,C.gold);
  panel(s,"伏笔","有没有忘记、重复或提前揭晓",50,335,370,125,C.blue);
  panel(s,"情节","是否推进目标，因果和结尾是否成立",440,335,370,125,C.green);
  panel(s,"文字","节奏、语气、重复和套话是否合适",830,335,400,125,C.gold);
  note(s,"AI 审阅只是第二意见；最后仍要由你完整通读。",525); footer(s,17);
}

// 18
addTwoColSlide("不满意时，先重写和比较版本","重写方式",[
  "按 AI 审阅意见修订",
  "输入你的具体要求后重写",
  "保留事件顺序，只调整对白或节奏"
],"版本操作",[
  "查看 v1、v2 等完整内容",
  "查看版本差异",
  "选择真正更合适的版本"
],"新版本不一定更好。每次都以你的故事目标和前文为准。");

// 19
{
  const s=deck.slides.add(); s.background.fill=C.white; title(s,"接受、应用、保存是连续的三个动作");
  steps(s,["接受候选稿\n认可当前版本","应用到章节草稿\n放入可编辑正文","作者再次通读\n手工修改","保存正文\n看到“已保存”"],{top:215});
  note(s,"不要在没有通读的情况下连续点击接受和应用。",510,C.red); footer(s,19);
}

// 20
addBulletsSlide("“接着写”适合卡文时快速准备一章",[
  "打开要接着写的章节，并确认正文已保存。",
  "进入“AI → AI 助手 → 接着写”。",
  "写一句“本章推进什么 + 暂时不要发生什么”。",
  "选择章节数、目标字数和保护设置后启动。",
  "写完会停下来，等你查看候选稿。",
  "第一次只做一章；不要一次塞入十几个要求。"
],"示例：接着写旧钥匙线索，但不要揭晓幕后人物。",{top:170,gap:62,size:21});

// 21
addTwoColSlide("多章续写也要逐章看，不是一次性采用","开始前",[
  "大纲和人物资料比较完整",
  "接下来几章目标明确",
  "第一次只设置 2—3 章"
],"运行中",[
  "每章结果保留为候选稿",
  "有问题就暂停，不要盲目跑完",
  "取消不会删除已生成的候选稿"
],"“继续下一章”只继续准备，不会采用当前章。");

// 22
addBulletsSlide("自动续写先设置四类保护",[
  "写作意图、目标章节数和每章目标字数。",
  "本次 AI 用量上限。",
  "序列结束、严重冲突和预算超出时停止。",
  "伏笔可能提前回收时停止。",
  "点击“保存保护设置”，再启动任务。",
  "自动续写只准备候选稿，不自动发书、不自动更新记忆。"
],"第一次自动续写仍建议只做 2—3 章。",{top:170,gap:62,size:21});

// 23
addTwoColSlide("暂停、停止和放弃，后果完全不同","还能恢复",[
  "暂停：暂时停下，作者可以继续",
  "停止：处理保护原因后可能恢复",
  "修复预算或冲突后回原任务点击继续"
],"不能恢复",[
  "放弃这次：任务永久取消",
  "已有候选稿仍然保留",
  "放弃前会二次确认"
],"调高预算、修复资料或关闭保护后，任务也不会自动恢复。",{rightAccent:C.red});

// 24
addBulletsSlide("大纲辅助的结果先进入草稿，再由你保存",[
  "先写清主角目标、主要阻力和接下来三章的大致推进。",
  "选择润色、扩写、续写或整理，并填写要求。",
  "对比“现在的大纲”和建议内容。",
  "检查冲突和建议是否已经过期。",
  "满意后点击“放进大纲”，回到大纲区再次检查。",
  "最后手动保存正式大纲。"
],"大纲在建议生成后被修改，旧建议会过期；重新读取后再生成。",{top:170,gap:62,size:21});

// 25
{
  const s=deck.slides.add(); s.background.fill=C.white; title(s,"人物、时间线和伏笔，是长篇不跑偏的基础");
  panel(s,"人物","姓名和别名\n当前目标与关系\n已经发生的重要变化",50,205,370,260,C.blue);
  panel(s,"时间线","事件实际发生顺序\n日期、季节和年份\n倒叙与并行故事线",440,205,370,260,C.green);
  panel(s,"伏笔","埋下、推进、回收\n首次出现章节\n何时可以揭晓",830,205,400,260,C.gold);
  note(s,"资料发生重大变化后及时更新；不要把整章正文复制进人物卡。",525); footer(s,25);
}

// 26
addTwoColSlide("@引用帮助系统找到正确资料","怎么使用",[
  "在正文输入 @ 和关键词",
  "从列表选择人物、事件或伏笔",
  "鼠标停留可查看摘要"
],"显示异常时",[
  "AI 建议引用会使用不同样式",
  "资料变化后引用可能失效",
  "重新输入 @ 并选择当前资料"
],"引用用于关联资料，不会把内部编号写进最终正文。");

// 27
addBulletsSlide("选区改写只改你选中的那一小段",[
  "选中文字，再选择扩写、缩写、润色或重写。",
  "扩写补细节；缩写去重复；润色改善表达；重写重新组织。",
  "等待新文后，对比原文和新文。",
  "需要时继续手工修改新文。",
  "满意才采用，不满意就拒绝。",
  "应用后重新通读上下文；发现不合适可以立即撤销。"
],"关键场景优先自己写，不要把整章反复交给局部改写。",{top:170,gap:62,size:21});

// 28
addTwoColSlide("风格画像和开篇助手，都只是参考","风格画像",[
  "选有代表性的自有章节作为样本",
  "样本太短时不要过度相信",
  "确认画像只表示允许后续参考"
],"开篇助手",[
  "先写故事想法，再选择开篇方向",
  "参考作品只分析结构，不复制原文",
  "前三章仍然是候选稿"
],"你可以停用、删除或重新提取风格画像；它不会锁死写法。");

// 29
addTwoColSlide("先看引用，再处理冲突","引用来源",[
  "已确认：来源仍一致",
  "已变化：按当前资料重新核对",
  "找不到来源：不要直接相信相关说法"
],"冲突等级",[
  "一般提示：帮助理解",
  "警告：知情后由作者决定",
  "阻断：必须真正处理后才能应用"
],"阻断冲突不能被当成普通警告跳过。",{rightAccent:C.red});

// 30
addBulletsSlide("应用正文以后，还要单独审阅故事记忆",[
  "候选稿可能建议更新人物、设定、事件、时间线或伏笔。",
  "逐项判断内容是否真的发生，而不是计划、猜测或假象。",
  "可以审批通过、编辑后通过、拒绝或稍后处理。",
  "一组建议确认后，再应用本组修订。",
  "正文采用和记忆更新是两个独立动作。"
],"只有作者确认并应用后，建议才进入正式故事记忆。",{gap:72});

// 31
addBulletsSlide("预算页面先回答三个问题",[
  "本月预计用了多少钱？",
  "本月预算还剩多少？",
  "当前预算状态是否允许继续？",
  "作品可以继承默认预算，也可以单独设置。",
  "手填价格前必须核对模型服务商官方说明。",
  "费用或用量不明时，系统会保护性停下。"
],"调高预算不会自动继续任务；回到原功能，由你点击继续。",{top:170,gap:62,size:21});

// 32
addTwoColSlide("创作分析帮你发现现象，不给作品打分","可以观察",[
  "篇幅、节奏和高潮间隔",
  "对白比例和常用词",
  "风格变化和候选稿使用情况"
],"正确理解",[
  "长篇可能使用缓存",
  "正文变化后可重新统计",
  "AI 使用分析不是 AI 文本检测"
],"看到异常数字后，回到对应章节亲自阅读，再决定是否修改。");

// 33
addTwoColSlide("按钮不见、变灰或任务停住，先找原因","入口问题",[
  "去设置中心检查助手开关",
  "确认已选章节并完成 AI 配置",
  "检查是否有未保存修改"
],"任务问题",[
  "查看是否等待方向、计划或审阅",
  "检查预算、冲突和伏笔保护",
  "处理后回原任务手动继续"
],"不要连续创建多个相同任务，也不要靠刷新绕过提示。",{rightAccent:C.red});

// 34
addBulletsSlide("每天写一章，按这个顺序最稳",[
  "开始前：看上一章结尾、本章目标、人物和伏笔。",
  "写作中：关键场景自己写；卡住时再用接着写。",
  "局部表达不满意时，只对选中内容改写。",
  "候选稿完成后，查看全文、引用、审阅和冲突。",
  "满意才接受和应用；然后自己修改并保存。",
  "最后审阅故事记忆，再进入下一章。"
],"每写完 3—5 章，再更新大纲、时间线、伏笔，并查看费用和创作分析。",{top:170,gap:62,size:21});

// 35
{
  const s=deck.slides.add(); s.background.fill=C.white; title(s,"封版使用前，完成最后十项检查");
  twoCol(s,"作品与配置",[
    "✓ 章节可以正常打开和保存",
    "✓ 模型连接测试成功",
    "✓ 写作助手可在设置中心开关",
    "✓ 预算保护已经设置",
    "✓ 写作上下文可以构建"
  ],"安全与确认",[
    "✓ 方向和计划必须由作者确认",
    "✓ 候选稿不会自动进正文",
    "✓ 阻断冲突不能跳过",
    "✓ 故事记忆单独审批",
    "✓ 停止任务不会自动恢复"
  ],{noteText:"全部确认后，再开始较长的多章或自动续写任务。"}); footer(s,35);
}

// 36
{
  const s=deck.slides.add(); s.background.fill=C.white;
  text(s,"最后只记住这一条",50,70,1180,54,20,true,C.muted,"center");
  text(s,"先决定方向\n再准备候选\n看过、改过、确认过\n最后才进入正文",180,180,920,300,48,true,C.ink,"center");
  shape(s,"rect",{left:240,top:535,width:800,height:3},C.accent);
  text(s,"你始终是作者。",50,570,1180,54,28,true,C.blue,"center"); footer(s,36);
}

await fs.mkdir(qa,{recursive:true});
for(const [i,slide] of deck.slides.items.entries()){
  const stem=`slide-${String(i+1).padStart(2,"0")}`;
  const png=await deck.export({slide,format:"png",scale:1});
  await fs.writeFile(path.join(qa,`${stem}.png`),new Uint8Array(await png.arrayBuffer()));
  const layout=await slide.export({format:"layout"});
  await fs.writeFile(path.join(qa,`${stem}.layout.json`),await layout.text());
}
const montage=await deck.export({format:"png",montage:true,scale:0.5});
await fs.writeFile(path.join(qa,"montage.png"),new Uint8Array(await montage.arrayBuffer()));
const pptx=await PresentationFile.exportPptx(deck);
await pptx.save(output);
console.log(output);
