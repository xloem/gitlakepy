MAXFILESIZE=100000
MAXFILECOUNT=256

# unpack all packfiles
mv objects/pack/* . 2>/dev/null &&
for pack in *.pack; do
	git unpack-objects < "$pack" && rm -vf "$pack"
done

# make small object stores, can use dirsplit
prefix="$(date --iso=seconds)"
dirsplit -L --accuracy 1 --prefix "alt-$prefix-" --blksize $((MAXFILESIZE)) --size=$(((MAXFILECOUNT-1) * MAXFILESIZE)) objects

# upload each dir, accumulating the upload into an alternates file
LONGEST_TXID=43
ALTERNATES_DEPTH=0 # it is not actually a tree, as i am confused.
touch alternates-$ALTERNATES_DEPTH
for dir in alt-${prefix}-*
do
	NEXT_SIZE=$((LONGEST_TXID + 1))
	for alternates_file in alternates-*
	do
		NEXT_SIZE=$((NEXT_SIZE + $(stat -c %s "$alternates_file")))
	done
	if ((NEXT_SIZE >= MAXFILESIZE))
	then
		cat alternates-* > "$dir"/info/alternates
		sed 's!^!../!' alternates-* > objects/info/alternates
		rm alternates-*
		touch alternates-0
		ALTERNATES_DEPTH=1
	fi
	if ! arkb deploy "$dir" -v --no-colors --concurrency 256 --auto-confirm --use-bundler https://node2.bundlr.network --timeout $((60*60*1000)) --tag-name Type --tag-value git-object-store | tee ../"$dir".arkb.log; then exit -1; fi
	txid="$(tail -n 1 ../"$dir".arkb.log | cut -d '/' -f 4)"
	TXID_LEN=$(($(echo -n "$txid" | wc -c)))
	if (( TXID_LEN != LONGEST_TXID ))
	then
		exit -1
	fi
	if ! curl -v https://arweave.net/"$txid"; then exit -1; fi
	if ! mv "$dir" "../$txid"; then exit -1; fi
	rm ../"$txid"/*/manifest.arkb
	echo "../$txid" >> alternates-$((ALTERNATES_DEPTH))
	{ cd ../$txid; find -type f; } | { cd objects; xargs rm -vrf; }
	sed 's!^!../!' alternates-$((ALTERNATES_DEPTH)) > objects/info/alternates
	ALTERNATES_DEPTH=0
done

cat alternates-* > objects/info/alternates

rm -rf git-dir 2>/dev/null
mkdir git-dir
cp -va description config info refs HEAD packed-refs objects   git-dir/

if ! arkb deploy git-dir -v --concurrency 256 --auto-confirm --use-bundler https://node2.bundlr.network --timeout $((60*60*1000)) --tag-name Type --tag-value git-dir | tee ../git.arkb.log; then exit -1; fi
rm -rf git-dir
