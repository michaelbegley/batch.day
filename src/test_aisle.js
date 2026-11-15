// Unit checks for the shop's store sections and staples. Run: node test_aisle.js (prints JSON; exit 1 on a miss)
const E=require('./engine.js'),fs=require('fs');
const A=E.AISLES,P=0,M=1,D=2,B=3,C=4,G=5,S=6,F=7,O=8;
const want={
 // the sample recipe
 'boneless chicken thighs':M,'Salt & black pepper':S,'ginger paste':C,'garlic powder':S,'Neutral oil':S,'Green onion whites':P,'garlic':P,'chicken bone broth':C,'coconut milk':C,'red curry paste':C,'soy sauce':C,'jasmine rice':G,'Baby bok choy':P,'Green onion tops':P,'Fresh lime juice':P,'Chili oil':S,
 // chili
 'ground beef':M,'yellow onion':P,'kidney beans':C,'crushed tomatoes':C,'tomato paste':C,'chili powder':S,'cumin':S,'beef broth':C,'shredded cheddar':D,'sour cream':D,'tortilla chips':G,'jalapeños':P,
 // baking
 'all-purpose flour':G,'baking powder':G,'baking soda':G,'granulated sugar':G,'brown sugar':G,'unsalted butter':D,'eggs':D,'vanilla extract':S,'whole milk':D,'chocolate chips':G,'cocoa powder':G,'powdered sugar':G,'cream of tartar':S,
 // pasta night
 'spaghetti':G,'marinara sauce':C,'Italian sausage':M,'parmesan':D,'fresh basil':P,'dried oregano':S,'olive oil':S,'red pepper flakes':S,'garlic bread':B,'baby spinach':P,'heavy cream':D,
 // tacos and breakfast
 'corn tortillas':B,'flour tortillas':B,'pork shoulder':M,'cilantro':P,'limes':P,'white onion':P,'salsa verde':C,'avocado':P,'queso fresco':D,'black beans':C,'bacon':M,'hamburger buns':B,'frozen peas':F,'frozen corn':F,'vanilla ice cream':F,'shrimp':M,'salmon fillets':M,'bell pepper':P,'red bell peppers':P,'cayenne pepper':S,'sea salt':S,'peanut butter':C,'honey':C,'maple syrup':C,'rice vinegar':S,'sesame oil':S,'eggplant':P,'butternut squash':P,'egg noodles':G,'cauliflower rice':P,'green beans':P,'chickpeas':C,'canned tuna':C,'Greek yogurt':D,'rolled oats':G,'lentils':G,'quinoa':G,'breadcrumbs':G,'panko':G,'cornstarch':G,'bay leaves':S,'smoked paprika':S,'garlic cloves':P,'ground ginger':S,'fresh ginger':P,'water':O,'ice':O,'white wine':O,'sweet potatoes':P,'russet potatoes':P,'mushrooms':P,'tofu':P,'fish sauce':C,'Dijon mustard':C,'mayonnaise':C,'dill pickles':C,'feta':D,'naan':B,'pita bread':B,'almonds':G,'walnuts':G,'chicken stock':C,'cream of mushroom soup':C,'diced tomatoes':C,'tomatoes':P,'cherry tomatoes':P,'lemon juice':P,'orange juice':C,'turkey':M,'cinnamon':S,'taco seasoning':S,'cooking spray':S,'kosher salt':S,'buttermilk':D,'cream cheese':D,'evaporated milk':C
};
const R=[];let bad=0;
const log=(n,ok,note)=>{R.push([n,ok?'ok':'FAIL',String(note||'')]);if(!ok)bad++};
const miss=Object.keys(want).filter((k)=>E.aisleOf(k)!==want[k]).map((k)=>`${k}: got ${A[E.aisleOf(k)]}, want ${A[want[k]]}`);
log(`aisleOf puts ${Object.keys(want).length} US grocery items in the right section`,!miss.length,miss.join('; '));
log('nine sections in store order',A.join('|')==='Produce|Meat & seafood|Dairy & eggs|Bakery|Canned & jarred|Dry goods & grains|Spices & oils|Frozen|Other');
log('odd input lands in Other, never throws',[null,undefined,'',42,'   ','🙂','xyzzy'].every((x)=>E.aisleOf(x)===8));
const t=fs.readFileSync('template.html','utf8'),s=t.match(/const SAMPLE=`([\s\S]*?)`;/)[1],p=E.batchDay(E.parseRecipe(s),14);
const g=E.aisles(p.grocery);
log('sample: sections come out in store order',g.map((x)=>x.name).join('|')==='Produce|Meat & seafood|Canned & jarred|Dry goods & grains|Spices & oils',g.map((x)=>x.name+':'+x.items.length).join(' '));
log('sample: every item is in exactly one section',g.reduce((n,x)=>n+x.items.length,0)===p.grocery.length);
log('sample: order inside a section is the recipe order',g[0].items.map((i)=>i.name).join('|')==='Green onion whites|garlic|Baby bok choy|Green onion tops|Fresh lime juice',g[0].items.map((i)=>i.name).join('|'));
log('aisles leaves the list it was given alone',p.grocery[0].name==='boneless chicken thighs'&&E.aisles([]).length===0&&E.aisles(null).length===0);
log('stapleKey: case, spaces, punctuation and plurals fold together',E.stapleKey(' Olive  Oil ')==='olive oil'&&E.stapleKey('Eggs')===E.stapleKey('egg')&&E.stapleKey('Tomatoes')===E.stapleKey('tomato')&&E.stapleKey('Salt & black pepper')==='salt black pepper'&&E.stapleKey('berries')===E.stapleKey('berry')&&E.stapleKey('swiss')==='swiss'&&E.stapleKey(null)==='',[E.stapleKey('Eggs'),E.stapleKey('Tomatoes'),E.stapleKey('Salt & black pepper')].join('|'));
const sl=E.shopList(p.grocery,[E.stapleKey('soy sauce'),E.stapleKey('neutral oil'),E.stapleKey('Ginger Paste')]);
log('shopList: staples leave the sections and go to the pantry',sl.pantry.map((i)=>i.name).join('|')==='ginger paste|soy sauce|Neutral oil'&&sl.buy.length===p.grocery.length-3&&!sl.buy.some((i)=>/soy|neutral oil|ginger paste/i.test(i.name)),sl.pantry.map((i)=>i.name).join('|'));
log('shopList: buy is the sections laid end to end',sl.groups.reduce((o,x)=>o.concat(x.items),[]).map((i)=>i.name).join('|')===sl.buy.map((i)=>i.name).join('|'));
log('shopList: no staples means nothing in the pantry',E.shopList(p.grocery).pantry.length===0&&E.shopList(p.grocery,new Set()).buy.length===p.grocery.length);
console.log(JSON.stringify(R));process.exit(bad?1:0);
