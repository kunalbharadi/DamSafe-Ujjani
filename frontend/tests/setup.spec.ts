import { test, expect } from '@playwright/test';

test('setup overview and connected readiness journey',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');
 await expect(page.getByRole('heading',{name:'Before the first Ujjani simulation.'})).toBeVisible();
 await expect(page.getByText('A domain starts with evidence.')).toBeVisible();
 await page.screenshot({path:'../docs/evidence/setup-desktop.png',fullPage:true});
 await page.getByRole('button',{name:'Open data library'}).click();
 await expect(page.getByRole('heading',{name:'Source register'})).toBeVisible();
 await page.getByRole('button',{name:'Scenarios',exact:false}).first().click();
 await expect(page.getByLabel('Scenario contract')).toBeVisible();
 await page.getByRole('button',{name:'Readiness',exact:false}).first().click();
 await expect(page.getByRole('heading',{name:'Inputs need review'})).toBeVisible();
 await expect(page.getByText('Verify downstream domain bounds', {exact:false})).toBeVisible();
 await page.getByRole('button',{name:'Run project audit'}).click();
 await expect(page.getByText('SUCCEEDED',{exact:true}).first()).toBeVisible({timeout:10000});
 await expect(page.getByText('Inputs need review',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Numerical runs',exact:false}).first().click();
 await expect(page.getByRole('heading',{name:'Engine examples'})).toBeVisible();
 await expect(page.getByText('These are laboratory or schematic examples',{exact:false})).toBeVisible();
 await page.setViewportSize({width:390,height:844});
 await page.getByRole('button',{name:'Overview',exact:false}).first().click();
 await page.screenshot({path:'../docs/evidence/setup-mobile.png',fullPage:true});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 expect(errors).toEqual([]);
});
