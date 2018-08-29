# trans
android translate string migration

处理的情况：
1、合并同一个用户在不同位置的注释到同一个位置, 放在</resource>之前；
2、对于target中没有的属性，则直接将source中定义的属性移植到target文件中；
3、对于target文件中未修改的属性，在source文件中做了修改，则保留source中的修改，滤除target中的修改；
4、对于source和target中都做了修改的属性，则只保留target中的属性，去掉source中的属性；
